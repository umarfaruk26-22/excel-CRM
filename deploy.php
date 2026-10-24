<?php
// ==============================================================================
// Automated Git Deployment Hook for excel-CRM
// URL: https://nexalogictechno.com/excel-crm/deploy.php
// Can be called via browser, curl, or GitHub Webhooks
// ==============================================================================

header('Content-Type: application/json; charset=utf-8');

$app_dir       = __DIR__;
$socket_path   = $app_dir . '/gunicorn.sock';
$lock_file     = $app_dir . '/.gunicorn_boot.lock';
$boot_log      = $app_dir . '/gunicorn_boot.log';
$error_log     = $app_dir . '/gunicorn_error.log';
$access_log    = $app_dir . '/gunicorn_access.log';
$backend_host  = '127.0.0.1';
$backend_port  = 58450;
$venv_bin      = $app_dir . '/venv/bin';
$venv_python   = file_exists($venv_bin . '/python3') ? $venv_bin . '/python3' : $venv_bin . '/python';

$response = [
    'success' => false,
    'timestamp' => date('c'),
    'git_pull' => [],
    'backend_restarted' => false,
    'backend_alive' => false,
];

// 1. Fetch & Reset to latest origin/main
$git_output = [];
@exec("cd {$app_dir} && git fetch origin main 2>&1 && git reset --hard origin/main 2>&1", $git_output, $git_code);
$response['git_pull'] = $git_output;

// 2. Kill existing processes & clear locks
@exec("pkill -9 -f 'backend.app.main:app' 2>&1");
@exec("pkill -9 -f '{$backend_port}' 2>&1");
if (file_exists($socket_path)) @unlink($socket_path);
if (file_exists($lock_file)) @unlink($lock_file);

// 3. Start Gunicorn backend
if (file_exists($venv_python)) {
    $env_export = "export PYTHONPATH=\"{$app_dir}:\$PYTHONPATH\" && export PATH=\"{$venv_bin}:/opt/alt/python311/bin:/usr/local/bin:/usr/bin:/bin:\$PATH\" && export DB_TYPE=\"sqlite\" && export OPENBLAS_NUM_THREADS=1 && export MKL_NUM_THREADS=1 && export NUMEXPR_NUM_THREADS=1 && export OMP_NUM_THREADS=1 && export VECLIB_MAXIMUM_THREADS=1";
    $bind_args = "--bind unix:{$socket_path} --bind {$backend_host}:{$backend_port} -k uvicorn.workers.UvicornWorker";
    $cmd = "nohup bash -c \"cd {$app_dir} && {$env_export} && nohup {$venv_python} -m gunicorn {$bind_args} --workers 2 --timeout 120 --error-logfile {$error_log} --access-logfile {$access_log} --capture-output backend.app.main:app >> {$boot_log} 2>&1 < /dev/null &\" >> {$boot_log} 2>&1 &";
    @exec($cmd);
    $response['backend_restarted'] = true;

    for ($i = 0; $i < 15; $i++) {
        usleep(300000);
        if (file_exists($socket_path)) {
            $fp = @fsockopen("unix://{$socket_path}", -1, $errno, $errstr, 0.4);
            if ($fp) {
                fclose($fp);
                $response['backend_alive'] = true;
                $response['success'] = true;
                break;
            }
        }
    }
}

echo json_encode($response, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);

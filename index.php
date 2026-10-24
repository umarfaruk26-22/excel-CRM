<?php
// ==============================================================================
// High-Performance Reverse Proxy & Auto-Healing Daemon for FastAPI CRM
// Subdirectory: https://nexalogictechno.com/excel-crm
// ==============================================================================

$app_dir       = __DIR__;
$sub_path      = '/excel-crm';
$socket_path   = $app_dir . '/gunicorn.sock';
$backend_host  = '127.0.0.1';
$backend_port  = 58450;
$backend_url   = "http://{$backend_host}:{$backend_port}";
$boot_log      = $app_dir . '/gunicorn_boot.log';
$error_log     = $app_dir . '/gunicorn_error.log';
$access_log    = $app_dir . '/gunicorn_access.log';
$lock_file     = $app_dir . '/.gunicorn_boot.lock';
$venv_dir      = $app_dir . '/venv';

// Detect virtualenv python interpreter
$venv_python = null;
if (file_exists($venv_dir . '/bin/python3')) {
    $venv_python = $venv_dir . '/bin/python3';
} elseif (file_exists($venv_dir . '/bin/python')) {
    $venv_python = $venv_dir . '/bin/python';
}

// -----------------------------------------------------------------------------
// 1. Actions Dispatcher (?action=restart, ?action=pull, ?action=seed, ?action=status)
// -----------------------------------------------------------------------------
$action = $_GET['action'] ?? null;
if ($action) {
    header('Content-Type: text/html; charset=utf-8');
    echo "<!DOCTYPE html><html><head><title>System Action: {$action}</title>";
    echo "<style>body{background:#0b0f19;color:#e2e8f0;font-family:system-ui,-apple-system,sans-serif;padding:30px;line-height:1.6;}pre{background:#1e293b;padding:16px;border-radius:10px;border:1px solid #334155;color:#38bdf8;overflow-x:auto;}a{color:#818cf8;text-decoration:none;font-weight:600;}.btn{display:inline-block;padding:10px 20px;background:#4f46e5;color:#fff;border-radius:8px;margin-top:15px;margin-right:10px;}</style></head><body>";
    echo "<h2>⚙️ Executing Action: " . htmlspecialchars($action) . "</h2>";

    if ($action === 'restart') {
        @exec("pkill -9 -f 'backend.app.main:app' 2>&1");
        @exec("pkill -9 -f '{$backend_port}' 2>&1");
        if (file_exists($socket_path)) @unlink($socket_path);
        if (file_exists($lock_file)) @unlink($lock_file);
        echo "<pre>Killed previous CRM backend processes and cleaned socket locks.</pre>";
        start_backend($app_dir, $socket_path, $backend_host, $backend_port, $boot_log, $error_log, $access_log, $lock_file, $venv_python);
        echo "<pre>Backend start initiated. Waiting for socket/port...</pre>";
        for ($i = 0; $i < 15; $i++) {
            usleep(300000);
            if (is_backend_alive($socket_path, $backend_host, $backend_port)) {
                echo "<p style='color:#10b981;'><strong>✅ CRM Backend is now ALIVE and ready!</strong></p>";
                break;
            }
        }
    } elseif ($action === 'seed') {
        if ($venv_python) {
            @exec("cd {$app_dir} && {$venv_python} database/seed_admin.py 2>&1", $out, $ret);
            echo "<h3>Seed Admin Result:</h3><pre>" . htmlspecialchars(implode("\n", (array)$out)) . "</pre>";
        } else {
            echo "<p style='color:#ef4444;'>Virtualenv python not found.</p>";
        }
    } elseif ($action === 'status') {
        $alive = is_backend_alive($socket_path, $backend_host, $backend_port);
        echo "<p>Backend status: <strong>" . ($alive ? "<span style='color:#10b981;'>ALIVE</span>" : "<span style='color:#ef4444;'>DOWN</span>") . "</strong></p>";
        if (file_exists($boot_log)) {
            echo "<h3>Boot Log (Last 1000 bytes):</h3><pre>" . htmlspecialchars(substr(file_get_contents($boot_log), -1000)) . "</pre>";
        }
        if (file_exists($error_log)) {
            echo "<h3>Error Log (Last 1000 bytes):</h3><pre>" . htmlspecialchars(substr(file_get_contents($error_log), -1000)) . "</pre>";
        }
    }

    echo "<br><a class='btn' href='{$sub_path}/'>⬅️ Return to CRM Dashboard</a>";
    echo "<a class='btn' href='{$sub_path}/?action=restart'>🔄 Restart Backend</a>";
    echo "</body></html>";
    exit;
}

// -----------------------------------------------------------------------------
// 2. Diagnostics Endpoint (?__diag=1 or /__diag)
// -----------------------------------------------------------------------------
if (isset($_GET['__diag']) || (isset($_SERVER['REQUEST_URI']) && strpos($_SERVER['REQUEST_URI'], '/__diag') !== false)) {
    header('Content-Type: application/json; charset=utf-8');
    $disabled = explode(',', (string)ini_get('disable_functions'));
    $disabled = array_map('trim', $disabled);

    $diag = [
        'timestamp' => date('c'),
        'php_version' => PHP_VERSION,
        'app_dir' => $app_dir,
        'user' => function_exists('get_current_user') ? get_current_user() : 'unknown',
        'exec_allowed' => function_exists('exec') && !in_array('exec', $disabled),
        'fsockopen_allowed' => function_exists('fsockopen') && !in_array('fsockopen', $disabled),
        'curl_allowed' => function_exists('curl_init'),
        'venv_dir_exists' => is_dir($venv_dir),
        'venv_python_exists' => !empty($venv_python) && file_exists($venv_python),
        'socket_exists' => file_exists($socket_path),
        'backend_alive' => is_backend_alive($socket_path, $backend_host, $backend_port),
        'boot_log_tail' => file_exists($boot_log) ? substr(file_get_contents($boot_log), -1500) : null,
        'error_log_tail' => file_exists($error_log) ? substr(file_get_contents($error_log), -1500) : null,
    ];

    if ($diag['exec_allowed']) {
        @exec("ps aux | grep -E 'gunicorn|backend.app.main' | grep -v grep 2>&1", $ps_out);
        $diag['running_processes'] = $ps_out;
    }

    echo json_encode($diag, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES);
    exit;
}

// -----------------------------------------------------------------------------
// 3. Health Check
// -----------------------------------------------------------------------------
function is_backend_alive($socket_path, $host, $port) {
    // Check Unix domain socket first
    if (file_exists($socket_path)) {
        $fp = @fsockopen("unix://{$socket_path}", -1, $errno, $errstr, 0.4);
        if ($fp) {
            fclose($fp);
            return true;
        }
    }
    // Check TCP port
    $fp = @fsockopen($host, $port, $errno, $errstr, 0.4);
    if ($fp) {
        fclose($fp);
        return true;
    }
    return false;
}

// -----------------------------------------------------------------------------
// 4. Daemon Auto-Starter
// -----------------------------------------------------------------------------
function start_backend($app_dir, $socket_path, $host, $port, $boot_log, $error_log, $access_log, $lock_file, $venv_python) {
    if (!function_exists('exec')) {
        return;
    }

    // Prevent multiple requests from triggering concurrent spawns
    if (file_exists($lock_file) && (time() - filemtime($lock_file) < 20)) {
        return;
    }
    @touch($lock_file);

    // If socket exists but backend is not responding, remove stale socket
    if (file_exists($socket_path)) {
        @unlink($socket_path);
    }

    $venv_bin = $app_dir . '/venv/bin';
    if (!$venv_python || !file_exists($venv_python)) {
        $setup_cmd = "nohup bash -c \"cd {$app_dir} && /opt/alt/python311/bin/python3 -m venv venv && ./venv/bin/pip install --upgrade pip && ./venv/bin/pip install -r requirements.txt gunicorn\" >> {$boot_log} 2>&1 < /dev/null &";
        @exec($setup_cmd);
        return;
    }

    $gunicorn_cmd = "{$venv_python} -m gunicorn";
    $env_export = "export PYTHONPATH=\"{$app_dir}:\$PYTHONPATH\" && export PATH=\"{$venv_bin}:/opt/alt/python311/bin:/usr/local/bin:/usr/bin:/bin:\$PATH\" && export DB_TYPE=\"sqlite\" && export OPENBLAS_NUM_THREADS=1 && export MKL_NUM_THREADS=1 && export NUMEXPR_NUM_THREADS=1 && export OMP_NUM_THREADS=1 && export VECLIB_MAXIMUM_THREADS=1";
    
    // Bind to Unix domain socket & TCP fallback
    $bind_args = "--bind unix:{$socket_path} --bind {$host}:{$port} -k uvicorn.workers.UvicornWorker";
    
    $full_cmd = "cd {$app_dir} && {$env_export} && nohup {$gunicorn_cmd} {$bind_args} --workers 2 --timeout 120 --error-logfile {$error_log} --access-logfile {$access_log} --capture-output backend.app.main:app >> {$boot_log} 2>&1 < /dev/null &";

    @exec($full_cmd);
}

// -----------------------------------------------------------------------------
// 5. Ensure Backend is Running
// -----------------------------------------------------------------------------
if (!is_backend_alive($socket_path, $backend_host, $backend_port)) {
    start_backend($app_dir, $socket_path, $backend_host, $backend_port, $boot_log, $error_log, $access_log, $lock_file, $venv_python);
    
    // Patient polling: wait up to 8 seconds (20 iterations * 400ms)
    for ($i = 0; $i < 20; $i++) {
        usleep(400000);
        if (is_backend_alive($socket_path, $backend_host, $backend_port)) {
            if (file_exists($lock_file)) @unlink($lock_file);
            break;
        }
    }
}

// -----------------------------------------------------------------------------
// 6. Compute Backend Forward Path
// -----------------------------------------------------------------------------
$request_uri = $_SERVER['REQUEST_URI'];
$backend_path = preg_replace('#^/excel-crm(?=/|$)#', '', $request_uri);
if (empty($backend_path)) {
    $backend_path = '/';
}

$use_socket = file_exists($socket_path);

$ch = curl_init();

if ($use_socket) {
    curl_setopt($ch, CURLOPT_UNIX_SOCKET_PATH, $socket_path);
    curl_setopt($ch, CURLOPT_URL, "http://localhost" . $backend_path);
} else {
    curl_setopt($ch, CURLOPT_URL, $backend_url . $backend_path);
}

curl_setopt($ch, CURLOPT_CUSTOMREQUEST, $_SERVER['REQUEST_METHOD']);
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_HEADER, true);
curl_setopt($ch, CURLOPT_FOLLOWLOCATION, false);
curl_setopt($ch, CURLOPT_TIMEOUT, 60);

// Detect multipart/form-data
$content_type = $_SERVER['CONTENT_TYPE'] ?? $_SERVER['HTTP_CONTENT_TYPE'] ?? '';
$is_multipart = (stripos($content_type, 'multipart/form-data') !== false) || !empty($_FILES);

$req_headers = [];
$incoming_headers = function_exists('getallheaders') ? getallheaders() : [];

$host_header = $_SERVER['HTTP_HOST'] ?? 'nexalogictechno.com';

foreach ($incoming_headers as $name => $value) {
    $lower = strtolower($name);
    if ($lower === 'host') {
        $req_headers[] = "Host: {$host_header}";
        $req_headers[] = "X-Forwarded-Host: {$host_header}";
        $req_headers[] = "X-Forwarded-Proto: https";
        $req_headers[] = "X-Forwarded-Prefix: {$sub_path}";
        $req_headers[] = "X-Forwarded-For: " . ($_SERVER['REMOTE_ADDR'] ?? '');
    } elseif ($lower === 'content-type' && $is_multipart) {
        continue; // Let cURL set multipart boundary
    } elseif ($lower !== 'content-length') {
        $req_headers[] = "{$name}: {$value}";
    }
}

// Forward Request Body
if (in_array($_SERVER['REQUEST_METHOD'], ['POST', 'PUT', 'PATCH'])) {
    if ($is_multipart && !empty($_FILES)) {
        $post_fields = $_POST;
        foreach ($_FILES as $key => $file_info) {
            if (is_array($file_info['tmp_name'])) {
                foreach ($file_info['tmp_name'] as $idx => $tmp_path) {
                    if (is_uploaded_file($tmp_path)) {
                        $post_fields["{$key}[{$idx}]"] = new CURLFile(
                            $tmp_path,
                            $file_info['type'][$idx],
                            $file_info['name'][$idx]
                        );
                    }
                }
            } else {
                if (is_uploaded_file($file_info['tmp_name'])) {
                    $post_fields[$key] = new CURLFile(
                        $file_info['tmp_name'],
                        $file_info['type'],
                        $file_info['name']
                    );
                }
            }
        }
        curl_setopt($ch, CURLOPT_POSTFIELDS, $post_fields);
    } else {
        $raw_input = file_get_contents('php://input');
        if (!empty($raw_input)) {
            curl_setopt($ch, CURLOPT_POSTFIELDS, $raw_input);
        }
    }
}

curl_setopt($ch, CURLOPT_HTTPHEADER, $req_headers);

// Execute cURL Proxy
$response = curl_exec($ch);

// -----------------------------------------------------------------------------
// 7. Error Handling / Recovery Splash Screen
// -----------------------------------------------------------------------------
if ($response === false) {
    $curl_err = curl_error($ch);
    $curl_code = curl_errno($ch);
    curl_close($ch);

    $boot_err = file_exists($boot_log) ? htmlspecialchars(substr(file_get_contents($boot_log), -1200)) : 'No boot log.';
    $err_err  = file_exists($error_log) ? htmlspecialchars(substr(file_get_contents($error_log), -1200)) : 'No error log.';

    header('HTTP/1.1 503 Service Unavailable');
    header('Retry-After: 4');
    header('Content-Type: text/html; charset=utf-8');

    echo <<<HTML
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="refresh" content="4;url={$request_uri}">
  <title>Customer CRM Starting...</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0b0f19;
      --card-bg: rgba(17, 24, 39, 0.95);
      --border: rgba(255, 255, 255, 0.1);
      --primary: #4f46e5;
      --text: #f8fafc;
      --muted: #94a3b8;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      background: var(--bg);
      color: var(--text);
      font-family: 'Outfit', sans-serif;
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 20px;
    }
    .card {
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 40px;
      max-width: 580px;
      width: 100%;
      text-align: center;
      box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
    }
    .spinner-box { margin-bottom: 24px; }
    .spinner {
      width: 52px;
      height: 52px;
      margin: 0 auto;
      border: 3px solid rgba(79, 70, 229, 0.2);
      border-top-color: var(--primary);
      border-radius: 50%;
      animation: spin 0.9s cubic-bezier(0.4, 0, 0.2, 1) infinite;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    h1 { font-size: 1.75rem; font-weight: 700; margin-bottom: 12px; }
    p { color: var(--muted); font-size: 0.95rem; margin-bottom: 24px; line-height: 1.6; }
    .btn-group { display: flex; flex-wrap: wrap; gap: 12px; justify-content: center; margin-bottom: 24px; }
    .btn {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 10px 20px;
      border-radius: 10px;
      font-weight: 600;
      font-size: 0.9rem;
      text-decoration: none;
      transition: all 0.2s;
    }
    .btn-primary { background: var(--primary); color: #fff; }
    .btn-secondary { background: rgba(255, 255, 255, 0.08); color: #e2e8f0; border: 1px solid var(--border); }
    details {
      text-align: left;
      background: #0f172a;
      border: 1px solid var(--border);
      border-radius: 12px;
      padding: 14px 18px;
      margin-top: 14px;
    }
    summary { cursor: pointer; font-weight: 600; font-size: 0.88rem; color: #cbd5e1; }
    pre {
      margin-top: 12px;
      background: #020617;
      padding: 14px;
      border-radius: 8px;
      font-size: 0.8rem;
      color: #38bdf8;
      overflow-x: auto;
      white-space: pre-wrap;
      word-break: break-all;
    }
  </style>
</head>
<body>
  <div class="card">
    <div class="spinner-box">
      <div class="spinner"></div>
    </div>
    <h1>CRM Service Starting...</h1>
    <p>
      The Python FastAPI CRM backend is initializing on the server.
      This page will refresh automatically in <strong>4 seconds</strong>.
    </p>

    <div class="btn-group">
      <a href="{$request_uri}" class="btn btn-primary">🔄 Refresh Now</a>
      <a href="{$sub_path}/?action=restart" class="btn btn-secondary">⚡ Force Restart</a>
    </div>

    <details>
      <summary>🔍 Diagnostics & Boot Logs</summary>
      <p style="margin: 8px 0 4px; font-size: 0.82rem; color: #94a3b8;">cURL error: {$curl_err}</p>
      <pre><strong>Boot Log:</strong><br>{$boot_err}<br><br><strong>Error Log:</strong><br>{$err_err}</pre>
    </details>
  </div>
</body>
</html>
HTML;
    exit;
}

// -----------------------------------------------------------------------------
// 8. Output Response & Subdirectory Path Rewriting for HTML
// -----------------------------------------------------------------------------
$header_size = curl_getinfo($ch, CURLINFO_HEADER_SIZE);
$http_code   = curl_getinfo($ch, CURLINFO_HTTP_CODE);
curl_close($ch);

$response_headers = substr($response, 0, $header_size);
$response_body    = substr($response, $header_size);

http_response_code($http_code);

$is_html = false;
$raw_headers = preg_split("/\r\n|\n|\r/", $response_headers);
foreach ($raw_headers as $line) {
    $line = trim($line);
    if (!empty($line) && strpos($line, ':') !== false) {
        $lower_line = strtolower($line);
        if (strpos($lower_line, 'content-type:') !== false && strpos($lower_line, 'text/html') !== false) {
            $is_html = true;
        }
        if (strpos($lower_line, 'transfer-encoding:') === false && strpos($lower_line, 'content-length:') === false) {
            header($line, false);
        }
    }
}

// Rewrite root links in HTML responses so they point into /excel-crm/
if ($is_html && !empty($response_body)) {
    // Assets & Uploads
    $response_body = preg_replace('#\b(href|src)=([\'"])/assets/#i', '$1=$2' . $sub_path . '/assets/', $response_body);
    $response_body = preg_replace('#\b(href|src)=([\'"])/uploads/#i', '$1=$2' . $sub_path . '/uploads/', $response_body);

    // Common Page Links
    $pages = [
        'index.html', 'login.html', 'login', 'customers.html', 'customers',
        'customer-details.html', 'customer-details', 'imports.html', 'imports',
        'month-files.html', 'month-files', 'followups.html', 'followups',
        'call-history.html', 'call-history', 'reports.html', 'reports',
        'settings.html', 'settings', 'api/'
    ];
    foreach ($pages as $p) {
        $response_body = preg_replace('#\bhref=([\'"])/' . preg_quote($p, '#') . '#i', 'href=$1' . $sub_path . '/' . $p, $response_body);
    }

    // Root link href="/" -> href="/excel-crm/"
    $response_body = preg_replace('#\bhref=([\'"])/([\'"])#i', 'href=$1' . $sub_path . '/$2', $response_body);
}

echo $response_body;

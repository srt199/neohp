<?php

function sanitize($value) {
    if (is_array($value)) {
        $sanitized = [];
        foreach ($value as $key => $item) {
            $sanitized[$key] = sanitize($item);
        }
        return $sanitized;
    }

    if (is_string($value)) {
        return htmlspecialchars(trim($value), ENT_QUOTES, 'UTF-8');
    }

    return $value;
}

function connectDb($databaseName = null) {
    $driver = defined('DB_DRIVER') ? DB_DRIVER : 'mysql';

    if ($driver === 'sqlite') {
        $sqlitePath = $databaseName ?: (defined('DB_SQLITE_PATH') ? DB_SQLITE_PATH : ':memory:');
        $dsn = str_starts_with($sqlitePath, 'sqlite:') ? $sqlitePath : 'sqlite:' . $sqlitePath;
        $pdo = new PDO($dsn);
    } else {
        $host = defined('DB_HOST') ? DB_HOST : '127.0.0.1';
        $charset = defined('DB_CHARSET') ? DB_CHARSET : 'utf8mb4';
        $username = defined('DB_USER') ? DB_USER : '';
        $password = defined('DB_PASS') ? DB_PASS : '';
        $dbName = $databaseName ?: (defined('DB_NAME') ? DB_NAME : '');

        if ($dbName === '') {
            throw new InvalidArgumentException('Missing database name. Set DB_NAME or pass one to connectDb().');
        }

        $dsn = sprintf('%s:host=%s;dbname=%s;charset=%s', $driver, $host, $dbName, $charset);
        $pdo = new PDO($dsn, $username, $password);
    }

    $pdo->setAttribute(PDO::ATTR_ERRMODE, PDO::ERRMODE_EXCEPTION);
    $pdo->setAttribute(PDO::ATTR_DEFAULT_FETCH_MODE, PDO::FETCH_ASSOC);
    return $pdo;
}

function select($pdo, $conditions = '1=1', $extraSql = '', $tableName = null) {
    $tableName = $tableName ?: (defined('DB_DEFAULT_TABLE') ? DB_DEFAULT_TABLE : null);
    if (!$tableName) {
        throw new InvalidArgumentException('Missing table name. Pass select(..., ..., ..., $tableName) or define DB_DEFAULT_TABLE.');
    }

    $safeTable = preg_replace('/[^a-zA-Z0-9_]/', '', (string) $tableName);
    $sql = "SELECT * FROM `{$safeTable}`";
    $params = [];

    if (is_array($conditions) && !empty($conditions)) {
        $whereClauses = [];
        foreach ($conditions as $column => $value) {
            $safeColumn = preg_replace('/[^a-zA-Z0-9_]/', '', (string) $column);
            $placeholder = 'w_' . $safeColumn;
            $whereClauses[] = "`{$safeColumn}` = :{$placeholder}";
            $params[$placeholder] = $value;
        }
        $sql .= ' WHERE ' . implode(' AND ', $whereClauses);
    } elseif (is_string($conditions) && trim($conditions) !== '') {
        $sql .= ' WHERE ' . $conditions;
    }

    if (is_string($extraSql) && trim($extraSql) !== '') {
        $sql .= ' ' . $extraSql;
    }

    $stmt = $pdo->prepare($sql);
    $stmt->execute($params);
    return $stmt->fetchAll(PDO::FETCH_ASSOC);
}

function insert($pdo, $tableName, $data) {
    if (!is_array($data) || empty($data)) {
        throw new InvalidArgumentException('insert() expects a non-empty associative array in the third parameter.');
    }

    $safeTable = preg_replace('/[^a-zA-Z0-9_]/', '', (string) $tableName);
    $columns = array_keys($data);
    $safeColumns = array_map(function ($col) {
        return preg_replace('/[^a-zA-Z0-9_]/', '', (string) $col);
    }, $columns);

    $placeholders = array_map(function ($col) {
        return ':' . $col;
    }, $safeColumns);

    $sql = sprintf(
        "INSERT INTO `%s` (`%s`) VALUES (%s)",
        $safeTable,
        implode('`, `', $safeColumns),
        implode(', ', $placeholders)
    );

    $bindData = [];
    foreach ($safeColumns as $idx => $safeCol) {
        $originalKey = $columns[$idx];
        $bindData[$safeCol] = $data[$originalKey];
    }

    $stmt = $pdo->prepare($sql);
    $stmt->execute($bindData);
    return (int) $pdo->lastInsertId();
}

function dbQuery($pdo, $sql, $params = []) {
    $stmt = $pdo->prepare($sql);
    $stmt->execute($params);
    return $stmt->fetchAll(PDO::FETCH_ASSOC);
}

function pingTelegram($botId, $message, $chatId = null) {
    $chatId = $chatId ?: (defined('TELEGRAM_CHAT_ID') ? TELEGRAM_CHAT_ID : null);
    if (!$botId || !$chatId || !$message) {
        return false;
    }

    $url = 'https://api.telegram.org/bot' . $botId . '/sendMessage';
    $payload = [
        'chat_id' => $chatId,
        'text' => $message,
    ];

    $ch = curl_init($url);
    curl_setopt_array($ch, [
        CURLOPT_POST => true,
        CURLOPT_POSTFIELDS => http_build_query($payload),
        CURLOPT_RETURNTRANSFER => true,
        CURLOPT_TIMEOUT => 20,
    ]);

    $response = curl_exec($ch);
    $code = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $error = curl_error($ch);
    curl_close($ch);

    return !$error && $code >= 200 && $code < 300 && $response !== false;
}

function postRequest($url, $data = [], $extraHeaders = []) {
    return httpRequest($url, 'post', $extraHeaders, $data);
}

function httpRequest($url, $method = 'get', $headers = [], $arrayData = []) {
    $method = strtoupper((string) $method);
    $ch = curl_init();

    if ($method === 'GET' && !empty($arrayData)) {
        $separator = str_contains($url, '?') ? '&' : '?';
        $url .= $separator . http_build_query($arrayData);
    }

    curl_setopt($ch, CURLOPT_URL, $url);
    curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
    curl_setopt($ch, CURLOPT_TIMEOUT, 30);

    if (!empty($headers)) {
        curl_setopt($ch, CURLOPT_HTTPHEADER, $headers);
    }

    if (in_array($method, ['POST', 'PUT', 'PATCH', 'DELETE'], true)) {
        curl_setopt($ch, CURLOPT_CUSTOMREQUEST, $method);
        if (!empty($arrayData)) {
            curl_setopt($ch, CURLOPT_POSTFIELDS, http_build_query($arrayData));
        }
    }

    $response = curl_exec($ch);
    $statusCode = (int) curl_getinfo($ch, CURLINFO_HTTP_CODE);
    $error = curl_error($ch);
    curl_close($ch);

    if ($error || $response === false) {
        return [
            'ok' => false,
            'status' => $statusCode,
            'error' => $error ?: 'Request failed',
            'body' => null,
        ];
    }

    $decoded = json_decode($response, true);
    return [
        'ok' => $statusCode >= 200 && $statusCode < 300,
        'status' => $statusCode,
        'error' => null,
        'body' => $decoded !== null ? $decoded : $response,
    ];
}

function slugify($text) {
    $text = (string) $text;
    if (function_exists('transliterator_transliterate')) {
        $text = transliterator_transliterate('Any-Latin; Latin-ASCII; Lower()', $text);
    }
    $text = preg_replace('~[^\pL\pN]+~u', '-', $text);
    return trim(strtolower((string) $text), '-');
}

function slugToWord($slug, $format = 'normal') {
    $words = str_replace('-', ' ', (string) $slug);
    return $format === 'fcaps' ? ucwords($words) : $words;
}

function parseValue($string, $delimiter, $index) {
    $parts = explode((string) $delimiter, (string) $string);
    $idx = (int) $index;
    return $parts[$idx] ?? null;
}

function readCsv($filepath, $delimiter = ',') {
    if (!file_exists($filepath) || !is_readable($filepath)) {
        return [];
    }

    $rows = [];
    $handle = fopen($filepath, 'r');
    if ($handle === false) {
        return [];
    }

    while (($row = fgetcsv($handle, 0, $delimiter)) !== false) {
        $rows[] = $row;
    }

    fclose($handle);
    return $rows;
}

function replaceInPageText($search, $replace) {
    $searchEsc = json_encode((string) $search, JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT);
    $replaceEsc = json_encode((string) $replace, JSON_HEX_TAG | JSON_HEX_AMP | JSON_HEX_APOS | JSON_HEX_QUOT);
    echo "<script>(function(){document.body.innerHTML=document.body.innerHTML.split($searchEsc).join($replaceEsc);})();</script>";
}

function setSession($key, $value) {
    if (session_status() !== PHP_SESSION_ACTIVE) {
        session_start();
    }
    $_SESSION[(string) $key] = $value;
    return $value;
}

function getSession($key, $default = null) {
    if (session_status() !== PHP_SESSION_ACTIVE) {
        session_start();
    }
    return $_SESSION[(string) $key] ?? $default;
}

function setLocalstorage($key, $value, $days = 30) {
    $expires = time() + ((int) $days * 86400);
    setcookie((string) $key, (string) $value, $expires, '/');
    $_COOKIE[(string) $key] = (string) $value;
    return $value;
}

function getLocalstorage($key, $default = null) {
    return $_COOKIE[(string) $key] ?? $default;
}

function redirect($url) {
    if (!headers_sent()) {
        header('Location: ' . $url);
    } else {
        echo '<script>window.location.href=' . json_encode($url) . ';</script>';
    }
    exit;
}

function respondJson($payload, $statusCode = 200) {
    if (!headers_sent()) {
        http_response_code((int) $statusCode);
        header('Content-Type: application/json; charset=utf-8');
    }
    echo json_encode($payload, JSON_UNESCAPED_UNICODE);
    exit;
}
<?php
// helpers.php
// This will contain all the callable functions from the neohp language,
// in php format. This should get included the generated php files

function pingTelegram($botId, $message) {
    $url = "https://api.telegram.org/bot" . $botId . "/sendMessage";
    $data = ['chat_id' => $GLOBALS['chat_id'] ?? '', 'text' => $message];
    // Use cURL or file_get_contents to send request
}

function slugify($text) {
    return strtolower(trim(preg_replace('/[^A-Za-z0-9-]+/', '-', $text)));
}

function slugToWord($slug, $format = 'normal') {
    $words = str_replace('-', ' ', $slug);
    return ($format === 'fcaps') ? ucwords($words) : $words;
}

function parseString($string, $delimiter, $index) {
    $parts = explode($delimiter, $string);
    return $parts[$index] ?? null;
}

// ... and so on for your other custom commands

?>
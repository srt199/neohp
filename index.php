<?php
include_once __DIR__ . '/helpers.php';

// SPDX-License-Identifier: MIT
// Copyright (c) 2026 Sergi Alvarez Triviño
include_once 'config.php';
ini_set('display_errors', '1');
ini_set('display_startup_errors', '1');
error_reporting(E_ALL); // enables ini errors
$arrayPost = sanitize($_POST); // gets all values received via post
$db = connectDb("dbName"); // reads host, dbname, user, pass from config.pyh profile id
$dbData = select($db, "active = 1", $extraSqlParams);
foreach ($dbData as $row) {
  if ($row['email'] == "john@gmail.com") {
    $email = "Email found";
    break;
  }
}

if ($arrayPost['customer'] == "on") {
  $isSale = TRUE;
} else { $isSale = FALSE; }

// More example funcs

insert($db, $tableName, ['name' => "james"]);
$array1 = ['name' => "john", 'email' => "john@gmail.com"];
insert($db, $tableName, $array1);

foreach (readCsv("cities.csv") as $city) {
  $cityPreview = $city;
  break;
}
?>
<div> <p> <?php
 echo $cityPreview;
?> </p> </div>

<?php

$url_slug = slugify(($_SERVER['REQUEST_URI'] ?? ''));
$product_name = slugToWord($url_slug, "fcaps"); // first letter of each word in caps
$cityName = parseValue($url_slug,"-", 2); // gets 3rd element separated by -. Functions are understood both with or without parentheses

// it replaces user visible text, so it can apply some php variable dynamically:
replaceInPageText("Texas", $cityName);

// other integrated functions
pingTelegram("", "This is your message"); // empty first param uses setTelegramConfig() defaults
postRequest($url, ['name' => "john", 'email' => "john@gmail.com"], $headers);
redirect("https://weblabs.es");
setSession("user_id", 5);
$user_id = getSession("user_id");
setLocalstorage("email", "john@gmail.com");
$email1 = getLocalstorage("email");
$users = dbQuery($db, "SELECT * FROM users WHERE active = 1"); // run any query
$response = httpRequest($url, "post", $headers, $arrayData);
$response_ok = $response['ok'];
$response_status = $response['status'];
$api_payload = $response['body'];

respondJson(['status' => "success", 'http_status' => $response_status, 'ok' => $response_ok, 'api' => $api_payload]); // exits and returns json headers

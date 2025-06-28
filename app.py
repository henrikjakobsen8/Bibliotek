import csv
import datetime
import os
from flask import Flask, request, render_template_string, redirect, url_for, flash

app = Flask(__name__)
app.secret_key = 'hemmelig_nogler'

BRUGERE_FIL = 'data/brugere.csv'
BOEGER_FIL = 'data/boeger.csv'
UDLAAN_FIL = 'data/udlaan.csv'

os.makedirs('data', exist_ok=True)

# HTML Template med designinspiration fra Vejlefjordskolen
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Bibliotek System</title>
    <style>
        :root {
            --primær-bg: #f8f9f4;
            --accent: #2a5d3b;
            --text-color: #333;
        }
        body {
            background: var(--primær-bg);
            color: var(--text-color);
            font-family: 'Segoe UI', sans-serif;
            margin: 0;
            padding: 0;
        }
        header {
            background: var(--accent);
            color: white;
            padding: 1em;
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        nav a {
            color: white;
            margin: 0 1em;
            text-decoration: none;
            font-weight: bold;
        }
        .hero {
            padding: 2em;
            background: #e8ede5;
            text-align: center;
        }
        .container {
            max-width: 800px;
            margin: auto;
            padding: 2em;
        }
        form {
            background: white;
            padding: 1em;
            margin-bottom: 1em;
            border-radius: 8px;
            box-shadow: 0 0 10px rgba(0,0,0,0.05);
        }
        input, button {
            padding: 0.5em;
            margin: 0.5em 0;
            width: 100%;
            border: 1px solid #ccc;
            border-radius: 4px;
        }
        button {
            background: var(--accent);
            color: white;
            cursor: pointer;
            font-weight: bold;
        }
        button:hover {
            background: #244a31;
        }
        ul {
            list-style: none;
            padding: 0;
        }
        li {
            background: #fff;
            margin-bottom: 0.5em;
            padding: 0.5em;
            border-left: 4px solid var(--accent);
        }
        .message {
            background: #fff3cd;
            padding: 1em;
            margin-bottom: 1em;
            border-left: 4px solid #ffeeba;
        }
    </style>
</head>
<body>
    <header>
        <h1>📚 Bibliotek</h1>
        <nav>
            <a href="/">Start</a>
            <a href="/udlaan-oversigt">Udlånsliste</a>
        </nav>
    </header>
    <section class="hero">
        <h2>Velkommen til Bibliotekssystemet</h2>
        <p>Scan, lån og aflever – nemt og hurtigt.</p>
    </section>
    <div class="container">
        <form method="POST" act

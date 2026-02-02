from flask import Flask, render_template, jsonify, request, redirect, url_for
import pandas as pd
from io import BytesIO
import random

app = Flask(__name__)

def parse_csv_bytes(data: bytes) -> pd.DataFrame:
    """Read CSV data; auto-fallback to header-less interpretation."""
    buf = BytesIO(data)
    raw = pd.read_csv(buf)
    cols = [str(c).lower() for c in raw.columns]
    if ("roll" in cols) or ("name" in cols):
        return raw
    # If headers look like data, retry with no header.
    buf.seek(0)
    return pd.read_csv(buf, header=None)


def normalize(raw: pd.DataFrame) -> pd.DataFrame:
    """Coerce into two columns: roll (int) and name (str)."""
    df_local = raw.copy()
    cols_lower = [str(c).lower() for c in df_local.columns]

    if "name" in cols_lower and "roll" in cols_lower:
        name_idx = cols_lower.index("name")
        roll_idx = cols_lower.index("roll")
        df_local = df_local.iloc[:, [roll_idx, name_idx]]
        df_local.columns = ["roll", "name"]
    elif df_local.shape[1] >= 2:
        df_local = df_local.iloc[:, :2]
        df_local.columns = ["name", "roll"]
        df_local = df_local[["roll", "name"]]
    else:
        df_local = df_local.iloc[:, :1]
        df_local.columns = ["name"]
        df_local["roll"] = range(1, len(df_local) + 1)
        df_local = df_local[["roll", "name"]]

    df_local["name"] = df_local["name"].astype(str).str.strip()
    df_local["roll"] = pd.to_numeric(df_local["roll"], errors="coerce")
    if df_local["roll"].isna().any():
        df_local["roll"] = range(1, len(df_local) + 1)
    df_local["roll"] = df_local["roll"].astype(int)
    df_local = df_local.sort_values("roll").reset_index(drop=True)
    return df_local


def load_from_path(path: str) -> pd.DataFrame:
    with open(path, "rb") as f:
        data = f.read()
    return normalize(parse_csv_bytes(data))


df = load_from_path("students.csv")

@app.route("/")
def index():
    students = df.to_dict(orient="records")
    return render_template("index.html", students=students)

@app.route("/pick")
def pick():
    row = df.sample(1).iloc[0]
    return jsonify({
        "roll": int(row["roll"].item()) if hasattr(row["roll"], "item") else int(row["roll"]),
        "name": row["name"]
    })

@app.route("/upload", methods=["GET", "POST"])
def upload():
    global df
    if request.method == "POST":
        file = request.files.get("file")
        if not file or file.filename == "":
            return render_template("upload.html", error="File select karo (CSV).")
        data = file.read()
        if not data:
            return render_template("upload.html", error="File empty hai.")
        try:
            new_df = normalize(parse_csv_bytes(data))
        except Exception:
            return render_template("upload.html", error="CSV parse nahi hua, please valid CSV upload karo.")
        new_df.to_csv("students.csv", index=False)
        df = new_df
        return redirect(url_for("index"))
    return render_template("upload.html")

if __name__ == "__main__":
    app.run(debug=True)

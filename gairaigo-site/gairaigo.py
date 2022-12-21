from app import app


if __name__ == "__main__":
    app.run(host='192.168.0.102', port=5000, debug=True, use_reloader=False)

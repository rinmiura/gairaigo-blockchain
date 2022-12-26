from app import app


if __name__ == "__main__":
    app.run(host='<your ip>', port=5000, debug=True, use_reloader=False)

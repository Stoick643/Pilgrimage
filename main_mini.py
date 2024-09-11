from flask import Flask, render_template

# app = create_app()

app = Flask(__name__)

if __name__ == '__main__':
    # app.run(debug=True)
    print("main start")
    app.run(host='127.0.0.1', port=5005, debug=True)  # Change the port to 8080


@app.route('/')
def index():
    print("Index route hit")
    return render_template('index.html')

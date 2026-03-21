from flask import Flask
from api.routes import api

app = Flask(__name__, static_folder="frontend", static_url_path="")
app.register_blueprint(api, url_prefix='/api')

@app.route('/')
def index():
    return app.send_static_file('index.html')

if __name__ == '__main__':
    app.run(debug=True)

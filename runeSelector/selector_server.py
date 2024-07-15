import flask
from flask.templating import render_template

app = flask.Flask()


@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")




if __name__ == "__main__":
    app.run(port=8030)
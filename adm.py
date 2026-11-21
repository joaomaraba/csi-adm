from curativos import app
from spe import spe_bp

app.register_blueprint(spe_bp)

if __name__ == "__main__":
    app.run(debug=True)
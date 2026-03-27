import base64
import os
import uuid
from datetime import datetime
from pathlib import Path

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    url_for,
)
from flask_login import (
    LoginManager,
    UserMixin,
    current_user,
    login_required,
    login_user,
    logout_user,
)
from flask_sqlalchemy import SQLAlchemy
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = STATIC_DIR / "uploads"
PDF_DIR = STATIC_DIR / "pdfs"

ALLOWED_EXTENSIONS = {
    "jpg", "jpeg", "png", "gif", "webp",
    "mp4", "mov", "avi", "mkv", "webm"
}


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", "dev-secret-cambiar-en-produccion")
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL",
    f"sqlite:///{BASE_DIR / 'inventario.db'}",
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
app.config["MAX_CONTENT_LENGTH"] = int(os.environ.get("MAX_CONTENT_LENGTH", 32 * 1024 * 1024))

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PDF_DIR.mkdir(parents=True, exist_ok=True)

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Debes iniciar sesión para continuar."


class Inmueble(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    direccion = db.Column(db.String(200), nullable=False)
    propietario = db.Column(db.String(200), nullable=False)
    fecha_recepcion = db.Column(db.String(50), nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"), nullable=False)

    inventarios = db.relationship(
        "Inventario",
        backref="inmueble",
        lazy=True,
        cascade="all, delete-orphan",
    )


class Inventario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inmueble_id = db.Column(db.Integer, db.ForeignKey("inmueble.id"), nullable=False)
    nombre = db.Column(db.String(200), nullable=False)
    fecha = db.Column(db.String(50), nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))

    secciones = db.relationship(
        "Seccion",
        backref="inventario",
        lazy=True,
        cascade="all, delete-orphan",
    )
    firmas = db.relationship(
        "Firma",
        backref="inventario_rel",
        lazy=True,
        cascade="all, delete-orphan",
    )


class Seccion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inventario_id = db.Column(db.Integer, db.ForeignKey("inventario.id"), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)

    fotos = db.relationship(
        "Foto",
        backref="seccion",
        lazy=True,
        cascade="all, delete-orphan",
    )
    observaciones = db.relationship(
        "Observacion",
        backref="seccion",
        lazy=True,
        cascade="all, delete-orphan",
    )


class Foto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seccion_id = db.Column(db.Integer, db.ForeignKey("seccion.id"), nullable=False)
    archivo = db.Column(db.String(255), nullable=False)


class Observacion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seccion_id = db.Column(db.Integer, db.ForeignKey("seccion.id"), nullable=False)
    comentario = db.Column(db.Text, nullable=False)


class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)

    inmuebles = db.relationship(
        "Inmueble",
        backref="usuario",
        lazy=True,
        cascade="all, delete-orphan",
    )


class Firma(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inventario_id = db.Column(db.Integer, db.ForeignKey("inventario.id"), nullable=False)
    nombre = db.Column(db.String(200), nullable=False)
    imagen = db.Column(db.Text, nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def unique_filename(filename: str) -> str:
    safe = secure_filename(filename)
    ext = safe.rsplit(".", 1)[1].lower()
    return f"{uuid.uuid4().hex}.{ext}"


def get_inmueble_owned_or_404(inmueble_id: int) -> Inmueble:
    inmueble = db.session.get(Inmueble, inmueble_id)
    if not inmueble:
        abort(404)
    if not current_user.is_authenticated or inmueble.usuario_id != current_user.id:
        abort(403)
    return inmueble


def get_inventario_owned_or_404(inventario_id: int) -> Inventario:
    inventario = db.session.get(Inventario, inventario_id)
    if not inventario:
        abort(404)
    if not current_user.is_authenticated or inventario.inmueble.usuario_id != current_user.id:
        abort(403)
    return inventario


def get_seccion_owned_or_404(seccion_id: int) -> Seccion:
    seccion = db.session.get(Seccion, seccion_id)
    if not seccion:
        abort(404)
    if not current_user.is_authenticated or seccion.inventario.inmueble.usuario_id != current_user.id:
        abort(403)
    return seccion


@app.route("/")
@login_required
def index():
    inmuebles = (
        Inmueble.query.filter_by(usuario_id=current_user.id)
        .order_by(Inmueble.id.desc())
        .all()
    )
    inmueble_ids = [i.id for i in inmuebles]

    total_inmuebles = len(inmuebles)
    total_inventarios = (
        Inventario.query.filter(Inventario.inmueble_id.in_(inmueble_ids)).count()
        if inmueble_ids else 0
    )
    total_fotos = (
        Foto.query.join(Seccion).join(Inventario).join(Inmueble)
        .filter(Inmueble.usuario_id == current_user.id)
        .count()
    )

    return render_template(
        "index.html",
        total_inmuebles=total_inmuebles,
        total_inventarios=total_inventarios,
        total_fotos=total_fotos,
        inmuebles=inmuebles,
    )


@app.route("/crear", methods=["POST"])
@login_required
def crear():
    direccion = request.form.get("direccion", "").strip()
    propietario = request.form.get("propietario", "").strip()
    fecha = request.form.get("fecha", "").strip()

    if not direccion or not propietario or not fecha:
        flash("Completa dirección, propietario y fecha.", "error")
        return redirect(url_for("index"))

    nuevo = Inmueble(
        direccion=direccion,
        propietario=propietario,
        fecha_recepcion=fecha,
        usuario_id=current_user.id,
    )
    db.session.add(nuevo)
    db.session.commit()
    flash("Inmueble creado correctamente.", "success")
    return redirect(url_for("index"))


@app.route("/inmueble/<int:id>")
@login_required
def ver_inmueble(id):
    inmueble = get_inmueble_owned_or_404(id)
    inventarios = (
        Inventario.query.filter_by(inmueble_id=id)
        .order_by(Inventario.id.desc())
        .all()
    )
    return render_template("inmueble.html", inmueble=inmueble, inventarios=inventarios)


@app.route("/crear_inventario/<int:id>", methods=["POST"])
@login_required
def crear_inventario(id):
    inmueble = get_inmueble_owned_or_404(id)
    nombre = request.form.get("nombre", "").strip()
    fecha = request.form.get("fecha", "").strip()

    if not nombre or not fecha:
        flash("Debes indicar nombre y fecha del inventario.", "error")
        return redirect(url_for("ver_inmueble", id=id))

    nuevo = Inventario(
        inmueble_id=inmueble.id,
        nombre=nombre,
        fecha=fecha,
        token=str(uuid.uuid4()),
    )
    db.session.add(nuevo)
    db.session.flush()

    secciones_base = ["Sala", "Cocina", "Comedor", "Habitación", "Baño", "Exterior"]
    for nombre_seccion in secciones_base:
        db.session.add(Seccion(inventario_id=nuevo.id, nombre=nombre_seccion))

    db.session.commit()
    flash("Inventario creado correctamente.", "success")
    return redirect(url_for("ver_inmueble", id=id))


@app.route("/inventario/<int:id>")
@login_required
def ver_inventario(id):
    inventario = get_inventario_owned_or_404(id)
    secciones = (
        Seccion.query.filter_by(inventario_id=id)
        .order_by(Seccion.id.asc())
        .all()
    )
    return render_template("inventario.html", inventario=inventario, secciones=secciones)


@app.route("/seccion/<int:id>")
@login_required
def ver_seccion(id):
    seccion = get_seccion_owned_or_404(id)
    fotos = Foto.query.filter_by(seccion_id=id).order_by(Foto.id.desc()).all()
    observaciones = (
        Observacion.query.filter_by(seccion_id=id)
        .order_by(Observacion.id.desc())
        .all()
    )
    return render_template(
        "seccion.html",
        seccion=seccion,
        fotos=fotos,
        observaciones=observaciones,
        inventario_id=seccion.inventario_id,
    )


@app.route("/subir_foto/<int:id>", methods=["POST"])
@login_required
def subir_foto(id):
    seccion = get_seccion_owned_or_404(id)
    archivos = request.files.getlist("fotos")
    guardados = 0

    for archivo in archivos:
        if not archivo or not archivo.filename:
            continue

        if not allowed_file(archivo.filename):
            flash(f"Archivo no permitido: {archivo.filename}", "error")
            continue

        nombre_archivo = unique_filename(archivo.filename)
        ruta = UPLOAD_DIR / nombre_archivo
        archivo.save(ruta)

        db.session.add(Foto(seccion_id=seccion.id, archivo=nombre_archivo))
        guardados += 1

    if guardados:
        db.session.commit()
        flash(f"Se subieron {guardados} archivo(s).", "success")
    else:
        db.session.rollback()

    return redirect(url_for("ver_seccion", id=id))


@app.route("/crear_observacion/<int:id>", methods=["POST"])
@login_required
def crear_observacion(id):
    seccion = get_seccion_owned_or_404(id)
    comentario = request.form.get("comentario", "").strip()

    if not comentario:
        flash("La observación no puede estar vacía.", "error")
        return redirect(url_for("ver_seccion", id=id))

    db.session.add(Observacion(seccion_id=seccion.id, comentario=comentario))
    db.session.commit()
    flash("Observación guardada.", "success")
    return redirect(url_for("ver_seccion", id=id))


@app.route("/crear_seccion/<int:id>", methods=["POST"])
@login_required
def crear_seccion(id):
    inventario = get_inventario_owned_or_404(id)
    nombre = request.form.get("nombre", "").strip()

    if not nombre:
        flash("Debes indicar el nombre de la sección.", "error")
        return redirect(url_for("ver_inventario", id=id))

    db.session.add(Seccion(inventario_id=inventario.id, nombre=nombre))
    db.session.commit()
    flash("Sección creada correctamente.", "success")
    return redirect(url_for("ver_inventario", id=id))


@app.route("/eliminar_seccion/<int:id>", methods=["POST"])
@login_required
def eliminar_seccion(id):
    seccion = get_seccion_owned_or_404(id)
    inventario_id = seccion.inventario_id
    db.session.delete(seccion)
    db.session.commit()
    flash("Sección eliminada.", "success")
    return redirect(url_for("ver_inventario", id=inventario_id))


@app.route("/editar_seccion/<int:id>", methods=["GET", "POST"])
@login_required
def editar_seccion(id):
    seccion = get_seccion_owned_or_404(id)

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        if not nombre:
            flash("El nombre no puede estar vacío.", "error")
            return redirect(url_for("editar_seccion", id=id))

        seccion.nombre = nombre
        db.session.commit()
        flash("Sección actualizada.", "success")
        return redirect(url_for("ver_inventario", id=seccion.inventario_id))

    return render_template("editar_seccion.html", seccion=seccion)


@app.route("/guardar_firma/<int:id>", methods=["POST"])
@login_required
def guardar_firma(id):
    inventario = get_inventario_owned_or_404(id)
    nombre = request.form.get("nombre", "").strip()
    imagen = request.form.get("firma", "").strip()

    if not nombre or not imagen or "," not in imagen:
        flash("Firma inválida.", "error")
        return redirect(url_for("ver_inventario", id=id))

    db.session.add(Firma(inventario_id=inventario.id, nombre=nombre, imagen=imagen))
    db.session.commit()
    flash("Firma guardada.", "success")
    return redirect(url_for("ver_inventario", id=id))


@app.route("/inventario_pdf/<int:id>")
@login_required
def inventario_pdf(id):
    inventario = get_inventario_owned_or_404(id)
    inmueble = inventario.inmueble
    secciones = Seccion.query.filter_by(inventario_id=id).order_by(Seccion.id.asc()).all()

    nombre_pdf = f"inventario_{id}.pdf"
    ruta_pdf = PDF_DIR / nombre_pdf

    styles = getSampleStyleSheet()
    elementos = []

    logo = STATIC_DIR / "logo.png"
    if logo.exists():
        elementos.append(Image(str(logo), width=120, height=60))
        elementos.append(Spacer(1, 10))

    elementos.append(Paragraph("INVENTARIO DE ENTREGA DE INMUEBLE", styles["Title"]))
    elementos.append(Spacer(1, 20))
    elementos.append(Paragraph(f"Dirección: {inmueble.direccion}", styles["BodyText"]))
    elementos.append(Paragraph(f"Propietario: {inmueble.propietario}", styles["BodyText"]))
    elementos.append(Paragraph(f"Fecha de recepción: {inmueble.fecha_recepcion}", styles["BodyText"]))
    elementos.append(Paragraph(f"Inventario: {inventario.nombre}", styles["BodyText"]))
    elementos.append(Paragraph(f"Fecha inventario: {inventario.fecha}", styles["BodyText"]))
    elementos.append(Spacer(1, 20))

    for seccion in secciones:
        elementos.append(Paragraph(f"Sección: {seccion.nombre}", styles["Heading2"]))
        elementos.append(Spacer(1, 10))

        for foto in seccion.fotos:
            ruta_archivo = UPLOAD_DIR / foto.archivo
            if not ruta_archivo.exists():
                continue

            ext = foto.archivo.rsplit(".", 1)[-1].lower()
            if ext in {"jpg", "jpeg", "png", "gif", "webp"}:
                elementos.append(Image(str(ruta_archivo), width=350, height=220))
            else:
                elementos.append(Paragraph(f"Video adjunto: {foto.archivo}", styles["BodyText"]))
            elementos.append(Spacer(1, 10))

        for observacion in seccion.observaciones:
            elementos.append(Paragraph(f"Observación: {observacion.comentario}", styles["BodyText"]))
            elementos.append(Spacer(1, 10))

        elementos.append(Spacer(1, 20))

    firmas = Firma.query.filter_by(inventario_id=id).order_by(Firma.id.asc()).all()
    if firmas:
        elementos.append(PageBreak())
        elementos.append(Paragraph("Firmas del inventario", styles["Title"]))
        elementos.append(Spacer(1, 40))

        for firma in firmas:
            elementos.append(Paragraph(f"Firmado por: {firma.nombre}", styles["BodyText"]))
            elementos.append(Spacer(1, 10))

            try:
                imagen_base64 = firma.imagen.split(",", 1)[1]
                imagen_bytes = base64.b64decode(imagen_base64)
                ruta_firma = UPLOAD_DIR / f"firma_{firma.id}.png"
                with open(ruta_firma, "wb") as fh:
                    fh.write(imagen_bytes)
                elementos.append(Image(str(ruta_firma), width=250, height=120))
                elementos.append(Spacer(1, 30))
            except Exception:
                elementos.append(Paragraph("No se pudo renderizar una firma.", styles["BodyText"]))
                elementos.append(Spacer(1, 20))

    pdf = SimpleDocTemplate(str(ruta_pdf), pagesize=letter)
    pdf.build(elementos)

    return redirect(url_for("static", filename=f"pdfs/{nombre_pdf}"))


@app.route("/publico/<string:token>")
def inventario_publico(token):
    inventario = Inventario.query.filter_by(token=token).first_or_404()
    secciones = (
        Seccion.query.filter_by(inventario_id=inventario.id)
        .order_by(Seccion.id.asc())
        .all()
    )
    return render_template(
        "inventario_publico.html",
        inventario=inventario,
        secciones=secciones,
    )


@app.route("/registro", methods=["GET", "POST"])
def registro():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        email = request.form.get("email", "").strip().lower()
        password_raw = request.form.get("password", "")

        if not nombre or not email or not password_raw:
            flash("Todos los campos son obligatorios.", "error")
            return redirect(url_for("registro"))

        existe = Usuario.query.filter_by(email=email).first()
        if existe:
            flash("Ese correo ya está registrado.", "error")
            return redirect(url_for("registro"))

        nuevo = Usuario(
            nombre=nombre,
            email=email,
            password=generate_password_hash(password_raw),
        )
        db.session.add(nuevo)
        db.session.commit()
        flash("Cuenta creada. Ahora puedes iniciar sesión.", "success")
        return redirect(url_for("login"))

    return render_template("registro.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and check_password_hash(usuario.password, password):
            login_user(usuario)
            flash("Bienvenido.", "success")
            next_url = request.args.get("next")
            return redirect(next_url or url_for("index"))

        flash("Credenciales inválidas.", "error")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Sesión cerrada.", "success")
    return redirect(url_for("login"))


@app.errorhandler(403)
def forbidden(_error):
    return render_template("403.html"), 403


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)

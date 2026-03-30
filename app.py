import base64
import os
import re
import uuid
from pathlib import Path

from flask import (
    Flask,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
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
from sqlalchemy import or_
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename


BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
UPLOAD_DIR = STATIC_DIR / "uploads"
PDF_DIR = STATIC_DIR / "pdfs"
DB_PATH = BASE_DIR / "inventario.db"

ALLOWED_EXTENSIONS = {
    "jpg",
    "jpeg",
    "png",
    "gif",
    "webp",
    "mp4",
    "mov",
    "avi",
    "mkv",
    "webm",
}

ROLE_ADMIN = "admin_empresa"
ROLE_EDITOR = "editor"
ROLE_VIEWER = "visor"
ROLE_SUPERADMIN = "superadmin"
EDIT_ROLES = {ROLE_SUPERADMIN, ROLE_ADMIN, ROLE_EDITOR}
VALID_ROLES = {ROLE_SUPERADMIN, ROLE_ADMIN, ROLE_EDITOR, ROLE_VIEWER}

STATUS_ACTIVE = "activa"
STATUS_SUSPENDED = "suspendida"
STATUS_CANCELLED = "cancelada"
VALID_COMPANY_STATUSES = {STATUS_ACTIVE, STATUS_SUSPENDED, STATUS_CANCELLED}

SUPERADMIN_NAME = os.environ.get("SUPERADMIN_NAME", "Propietario")
SUPERADMIN_EMAIL = os.environ.get("SUPERADMIN_EMAIL", "admin@inventario.local")
SUPERADMIN_PASSWORD = os.environ.get("SUPERADMIN_PASSWORD", "Admin123456!")
INTERNAL_COMPANY_SLUG = "plataforma-interna"


app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get(
    "SECRET_KEY", "dev-secret-cambiar-en-produccion"
)
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", f"sqlite:///{DB_PATH}"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)
app.config["MAX_CONTENT_LENGTH"] = int(
    os.environ.get("MAX_CONTENT_LENGTH", 32 * 1024 * 1024)
)

UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
PDF_DIR.mkdir(parents=True, exist_ok=True)

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Debes iniciar sesion para continuar."


class Empresa(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(150), nullable=False)
    slug = db.Column(db.String(160), unique=True, nullable=False, index=True)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    estado = db.Column(db.String(20), nullable=False, default=STATUS_ACTIVE)

    usuarios = db.relationship(
        "Usuario",
        backref="empresa",
        lazy=True,
        cascade="all, delete-orphan",
    )
    inmuebles = db.relationship(
        "Inmueble",
        backref="empresa",
        lazy=True,
        cascade="all, delete-orphan",
    )


class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(30), nullable=False, default=ROLE_ADMIN)
    activo = db.Column(db.Boolean, nullable=False, default=True)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresa.id"), nullable=False)


class Inmueble(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    direccion = db.Column(db.String(200), nullable=False)
    propietario = db.Column(db.String(200), nullable=False)
    fecha_recepcion = db.Column(db.String(50), nullable=False)
    empresa_id = db.Column(db.Integer, db.ForeignKey("empresa.id"), nullable=False)

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
    token = db.Column(
        db.String(100), unique=True, nullable=False, default=lambda: str(uuid.uuid4())
    )

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
    inventario_id = db.Column(
        db.Integer, db.ForeignKey("inventario.id"), nullable=False
    )
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


class Firma(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inventario_id = db.Column(
        db.Integer, db.ForeignKey("inventario.id"), nullable=False
    )
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


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or uuid.uuid4().hex[:8]


def unique_company_slug(name: str) -> str:
    base_slug = slugify(name)
    slug = base_slug
    counter = 2
    while Empresa.query.filter_by(slug=slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug


def user_can_edit(user) -> bool:
    return bool(user and user.is_authenticated and user.rol in EDIT_ROLES)


def user_is_superadmin(user) -> bool:
    return bool(user and user.is_authenticated and user.rol == ROLE_SUPERADMIN)


def user_is_admin(user) -> bool:
    return bool(user and user.is_authenticated and user.rol == ROLE_ADMIN)


def require_edit_permission() -> None:
    if not user_can_edit(current_user):
        abort(403)


def require_admin_permission() -> None:
    if not (user_is_admin(current_user) or user_is_superadmin(current_user)):
        abort(403)


def require_superadmin_permission() -> None:
    if not user_is_superadmin(current_user):
        abort(403)


def get_effective_company() -> Empresa | None:
    if not current_user.is_authenticated:
        return None
    if user_is_superadmin(current_user):
        company_id = session.get("superadmin_company_id")
        if not company_id:
            return None
        return db.session.get(Empresa, company_id)
    return current_user.empresa


def get_effective_company_id() -> int | None:
    empresa = get_effective_company()
    return empresa.id if empresa else None


def company_required() -> None:
    if not current_user.is_authenticated:
        abort(403)
    if user_is_superadmin(current_user):
        empresa = get_effective_company()
        if not empresa:
            abort(403)
        return
    if not getattr(current_user, "activo", True):
        logout_user()
        abort(403)
    if (
        not current_user.empresa
        or not current_user.empresa.activo
        or current_user.empresa.estado != STATUS_ACTIVE
    ):
        logout_user()
        abort(403)


def get_inmueble_for_current_company_or_404(inmueble_id: int) -> Inmueble:
    company_required()
    inmueble = db.session.get(Inmueble, inmueble_id)
    if not inmueble:
        abort(404)
    if inmueble.empresa_id != get_effective_company_id():
        abort(403)
    return inmueble


def get_inventario_for_current_company_or_404(inventario_id: int) -> Inventario:
    company_required()
    inventario = db.session.get(Inventario, inventario_id)
    if not inventario:
        abort(404)
    if inventario.inmueble.empresa_id != get_effective_company_id():
        abort(403)
    return inventario


def get_seccion_for_current_company_or_404(seccion_id: int) -> Seccion:
    company_required()
    seccion = db.session.get(Seccion, seccion_id)
    if not seccion:
        abort(404)
    if seccion.inventario.inmueble.empresa_id != get_effective_company_id():
        abort(403)
    return seccion


def get_foto_for_current_company_or_404(foto_id: int) -> Foto:
    company_required()
    foto = db.session.get(Foto, foto_id)
    if not foto:
        abort(404)
    if foto.seccion.inventario.inmueble.empresa_id != get_effective_company_id():
        abort(403)
    return foto


def get_user_for_current_company_or_404(user_id: int) -> Usuario:
    company_required()
    usuario = db.session.get(Usuario, user_id)
    if not usuario:
        abort(404)
    if usuario.empresa_id != current_user.empresa_id:
        abort(403)
    return usuario


@app.context_processor
def inject_access_context():
    empresa = get_effective_company()
    return {
        "current_company": empresa,
        "can_edit": user_can_edit(current_user),
        "is_superadmin": user_is_superadmin(current_user),
        "is_company_admin": user_is_admin(current_user),
        "ROLE_ADMIN": ROLE_ADMIN,
        "ROLE_EDITOR": ROLE_EDITOR,
        "ROLE_VIEWER": ROLE_VIEWER,
        "ROLE_SUPERADMIN": ROLE_SUPERADMIN,
        "STATUS_ACTIVE": STATUS_ACTIVE,
        "STATUS_SUSPENDED": STATUS_SUSPENDED,
        "STATUS_CANCELLED": STATUS_CANCELLED,
        "superadmin_company_mode": user_is_superadmin(current_user)
        and empresa is not None,
    }


@app.route("/")
@login_required
def index():
    if user_is_superadmin(current_user) and not get_effective_company():
        return redirect(url_for("superadmin_empresas"))

    company_required()
    search_query = request.args.get("q", "").strip()
    company_id = get_effective_company_id()

    base_query = Inmueble.query.filter_by(empresa_id=company_id)
    if search_query:
        search_pattern = f"%{search_query}%"
        base_query = base_query.filter(
            or_(
                Inmueble.direccion.ilike(search_pattern),
                Inmueble.propietario.ilike(search_pattern),
                Inmueble.inventarios.any(Inventario.nombre.ilike(search_pattern)),
            )
        )

    inmuebles = base_query.order_by(Inmueble.id.desc()).all()
    all_inmuebles = (
        Inmueble.query.filter_by(empresa_id=company_id)
        .order_by(Inmueble.id.desc())
        .all()
    )
    inmueble_ids = [inmueble.id for inmueble in all_inmuebles]

    total_inmuebles = len(all_inmuebles)
    total_inventarios = (
        Inventario.query.filter(Inventario.inmueble_id.in_(inmueble_ids)).count()
        if inmueble_ids
        else 0
    )
    total_fotos = (
        Foto.query.join(Seccion)
        .join(Inventario)
        .join(Inmueble)
        .filter(Inmueble.empresa_id == company_id)
        .count()
    )

    return render_template(
        "index.html",
        total_inmuebles=total_inmuebles,
        total_inventarios=total_inventarios,
        total_fotos=total_fotos,
        search_query=search_query,
        inmuebles=inmuebles,
    )


@app.route("/crear", methods=["POST"])
@login_required
def crear():
    company_required()
    require_edit_permission()
    company_id = get_effective_company_id()

    direccion = request.form.get("direccion", "").strip()
    propietario = request.form.get("propietario", "").strip()
    fecha = request.form.get("fecha", "").strip()

    if not direccion or not propietario or not fecha:
        flash("Completa direccion, propietario y fecha.", "error")
        return redirect(url_for("index"))

    nuevo = Inmueble(
        direccion=direccion,
        propietario=propietario,
        fecha_recepcion=fecha,
        empresa_id=company_id,
    )
    db.session.add(nuevo)
    db.session.commit()
    flash("Inmueble creado correctamente.", "success")
    return redirect(url_for("index"))


@app.route("/inmueble/<int:id>")
@login_required
def ver_inmueble(id):
    inmueble = get_inmueble_for_current_company_or_404(id)
    inventarios = (
        Inventario.query.filter_by(inmueble_id=id).order_by(Inventario.id.desc()).all()
    )
    return render_template("inmueble.html", inmueble=inmueble, inventarios=inventarios)


@app.route("/crear_inventario/<int:id>", methods=["POST"])
@login_required
def crear_inventario(id):
    require_edit_permission()
    inmueble = get_inmueble_for_current_company_or_404(id)
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

    secciones_base = ["Sala", "Cocina", "Comedor", "Habitacion", "Baño", "Exterior"]
    for nombre_seccion in secciones_base:
        db.session.add(Seccion(inventario_id=nuevo.id, nombre=nombre_seccion))

    db.session.commit()
    flash("Inventario creado correctamente.", "success")
    return redirect(url_for("ver_inmueble", id=id))


@app.route("/inventario/<int:id>")
@login_required
def ver_inventario(id):
    inventario = get_inventario_for_current_company_or_404(id)
    secciones = (
        Seccion.query.filter_by(inventario_id=id).order_by(Seccion.id.asc()).all()
    )
    return render_template(
        "inventario.html", inventario=inventario, secciones=secciones
    )


@app.route("/seccion/<int:id>")
@login_required
def ver_seccion(id):
    seccion = get_seccion_for_current_company_or_404(id)
    fotos = Foto.query.filter_by(seccion_id=id).order_by(Foto.id.desc()).all()
    observaciones = (
        Observacion.query.filter_by(seccion_id=id).order_by(Observacion.id.desc()).all()
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
    require_edit_permission()
    seccion = get_seccion_for_current_company_or_404(id)
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


@app.route("/eliminar_foto/<int:id>", methods=["POST"])
@login_required
def eliminar_foto(id):
    require_edit_permission()
    foto = get_foto_for_current_company_or_404(id)
    seccion_id = foto.seccion_id
    ruta = UPLOAD_DIR / foto.archivo
    db.session.delete(foto)
    db.session.commit()
    if ruta.exists():
        ruta.unlink(missing_ok=True)
    flash("Archivo eliminado.", "success")
    return redirect(url_for("ver_seccion", id=seccion_id))


@app.route("/crear_observacion/<int:id>", methods=["POST"])
@login_required
def crear_observacion(id):
    require_edit_permission()
    seccion = get_seccion_for_current_company_or_404(id)
    comentario = request.form.get("comentario", "").strip()

    if not comentario:
        flash("La observacion no puede estar vacia.", "error")
        return redirect(url_for("ver_seccion", id=id))

    db.session.add(Observacion(seccion_id=seccion.id, comentario=comentario))
    db.session.commit()
    flash("Observacion guardada.", "success")
    return redirect(url_for("ver_seccion", id=id))


@app.route("/crear_seccion/<int:id>", methods=["POST"])
@login_required
def crear_seccion(id):
    require_edit_permission()
    inventario = get_inventario_for_current_company_or_404(id)
    nombre = request.form.get("nombre", "").strip()

    if not nombre:
        flash("Debes indicar el nombre de la seccion.", "error")
        return redirect(url_for("ver_inventario", id=id))

    db.session.add(Seccion(inventario_id=inventario.id, nombre=nombre))
    db.session.commit()
    flash("Seccion creada correctamente.", "success")
    return redirect(url_for("ver_inventario", id=id))


@app.route("/eliminar_seccion/<int:id>", methods=["POST"])
@login_required
def eliminar_seccion(id):
    require_edit_permission()
    seccion = get_seccion_for_current_company_or_404(id)
    inventario_id = seccion.inventario_id
    db.session.delete(seccion)
    db.session.commit()
    flash("Seccion eliminada.", "success")
    return redirect(url_for("ver_inventario", id=inventario_id))


@app.route("/editar_seccion/<int:id>", methods=["GET", "POST"])
@login_required
def editar_seccion(id):
    seccion = get_seccion_for_current_company_or_404(id)

    if request.method == "POST":
        require_edit_permission()
        nombre = request.form.get("nombre", "").strip()
        if not nombre:
            flash("El nombre no puede estar vacio.", "error")
            return redirect(url_for("editar_seccion", id=id))

        seccion.nombre = nombre
        db.session.commit()
        flash("Seccion actualizada.", "success")
        return redirect(url_for("ver_inventario", id=seccion.inventario_id))

    return render_template("editar_seccion.html", seccion=seccion)


@app.route("/guardar_firma/<int:id>", methods=["POST"])
@login_required
def guardar_firma(id):
    require_edit_permission()
    inventario = get_inventario_for_current_company_or_404(id)
    nombre = request.form.get("nombre", "").strip()
    imagen = request.form.get("firma", "").strip()

    if not nombre or not imagen or "," not in imagen:
        flash("Firma invalida.", "error")
        return redirect(url_for("ver_inventario", id=id))

    db.session.add(Firma(inventario_id=inventario.id, nombre=nombre, imagen=imagen))
    db.session.commit()
    flash("Firma guardada.", "success")
    return redirect(url_for("ver_inventario", id=id))


@app.route("/inventario_pdf/<int:id>")
@login_required
def inventario_pdf(id):
    inventario = get_inventario_for_current_company_or_404(id)
    inmueble = inventario.inmueble
    secciones = (
        Seccion.query.filter_by(inventario_id=id).order_by(Seccion.id.asc()).all()
    )

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
    elementos.append(
        Paragraph(f"Empresa: {inmueble.empresa.nombre}", styles["BodyText"])
    )
    elementos.append(Paragraph(f"Direccion: {inmueble.direccion}", styles["BodyText"]))
    elementos.append(
        Paragraph(f"Propietario: {inmueble.propietario}", styles["BodyText"])
    )
    elementos.append(
        Paragraph(f"Fecha de recepcion: {inmueble.fecha_recepcion}", styles["BodyText"])
    )
    elementos.append(Paragraph(f"Inventario: {inventario.nombre}", styles["BodyText"]))
    elementos.append(
        Paragraph(f"Fecha inventario: {inventario.fecha}", styles["BodyText"])
    )
    elementos.append(Spacer(1, 20))

    for seccion in secciones:
        elementos.append(Paragraph(f"Seccion: {seccion.nombre}", styles["Heading2"]))
        elementos.append(Spacer(1, 10))

        for foto in seccion.fotos:
            ruta_archivo = UPLOAD_DIR / foto.archivo
            if not ruta_archivo.exists():
                continue

            ext = foto.archivo.rsplit(".", 1)[-1].lower()
            if ext in {"jpg", "jpeg", "png", "gif", "webp"}:
                elementos.append(Image(str(ruta_archivo), width=350, height=220))
            else:
                elementos.append(
                    Paragraph(f"Video adjunto: {foto.archivo}", styles["BodyText"])
                )
            elementos.append(Spacer(1, 10))

        for observacion in seccion.observaciones:
            elementos.append(
                Paragraph(f"Observacion: {observacion.comentario}", styles["BodyText"])
            )
            elementos.append(Spacer(1, 10))

        elementos.append(Spacer(1, 20))

    firmas = Firma.query.filter_by(inventario_id=id).order_by(Firma.id.asc()).all()
    if firmas:
        elementos.append(PageBreak())
        elementos.append(Paragraph("Firmas del inventario", styles["Title"]))
        elementos.append(Spacer(1, 40))

        for firma in firmas:
            elementos.append(
                Paragraph(f"Firmado por: {firma.nombre}", styles["BodyText"])
            )
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
                elementos.append(
                    Paragraph("No se pudo renderizar una firma.", styles["BodyText"])
                )
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
    flash(
        "El registro publico esta deshabilitado. Contacta al administrador de la plataforma.",
        "error",
    )
    return redirect(url_for("login"))


@app.route("/superadmin/empresas", methods=["GET", "POST"])
@login_required
def superadmin_empresas():
    require_superadmin_permission()

    if request.method == "POST":
        empresa_nombre = request.form.get("empresa", "").strip()
        admin_nombre = request.form.get("nombre", "").strip()
        email = request.form.get("email", "").strip().lower()
        password_raw = request.form.get("password", "")
        estado = request.form.get("estado", STATUS_ACTIVE).strip()

        if not empresa_nombre or not admin_nombre or not email or not password_raw:
            flash(
                "Empresa, admin, correo y contrasena temporal son obligatorios.",
                "error",
            )
            return redirect(url_for("superadmin_empresas"))

        if estado not in VALID_COMPANY_STATUSES:
            flash("Selecciona un estado valido para la empresa.", "error")
            return redirect(url_for("superadmin_empresas"))

        existe = Usuario.query.filter_by(email=email).first()
        if existe:
            flash("Ese correo ya esta registrado.", "error")
            return redirect(url_for("superadmin_empresas"))

        empresa = Empresa(
            nombre=empresa_nombre,
            slug=unique_company_slug(empresa_nombre),
            estado=estado,
            activo=True,
        )
        db.session.add(empresa)
        db.session.flush()

        nuevo = Usuario(
            nombre=admin_nombre,
            email=email,
            password=generate_password_hash(password_raw),
            empresa_id=empresa.id,
            rol=ROLE_ADMIN,
            activo=True,
        )
        db.session.add(nuevo)
        db.session.commit()
        flash("Empresa creada correctamente con su admin principal.", "success")
        return redirect(url_for("superadmin_empresas"))

    empresas = (
        Empresa.query.filter(Empresa.slug != INTERNAL_COMPANY_SLUG)
        .order_by(Empresa.nombre.asc())
        .all()
    )
    return render_template("superadmin_empresas.html", empresas=empresas)


@app.route("/superadmin/empresas/<int:id>/estado", methods=["POST"])
@login_required
def superadmin_actualizar_estado_empresa(id):
    require_superadmin_permission()
    empresa = db.session.get(Empresa, id)
    if not empresa:
        abort(404)

    estado = request.form.get("estado", "").strip()
    if estado not in VALID_COMPANY_STATUSES:
        flash("Selecciona un estado valido.", "error")
        return redirect(url_for("superadmin_empresas"))

    empresa.estado = estado
    empresa.activo = estado != STATUS_CANCELLED
    db.session.commit()

    if estado != STATUS_ACTIVE and session.get("superadmin_company_id") == empresa.id:
        session.pop("superadmin_company_id", None)

    flash("Estado de la empresa actualizado correctamente.", "success")
    return redirect(url_for("superadmin_empresas"))


@app.route("/superadmin/empresas/<int:id>/entrar", methods=["POST"])
@login_required
def superadmin_entrar_empresa(id):
    require_superadmin_permission()
    empresa = db.session.get(Empresa, id)
    if not empresa:
        abort(404)

    session["superadmin_company_id"] = empresa.id
    flash(f"Modo superadmin activo sobre {empresa.nombre}.", "success")
    return redirect(url_for("index"))


@app.route("/superadmin/salir-empresa", methods=["POST"])
@login_required
def superadmin_salir_empresa():
    require_superadmin_permission()
    session.pop("superadmin_company_id", None)
    flash("Saliste del modo empresa.", "success")
    return redirect(url_for("superadmin_empresas"))


@app.route("/usuarios", methods=["GET", "POST"])
@login_required
def usuarios():
    company_required()
    require_admin_permission()
    company_id = get_effective_company_id()

    if request.method == "POST":
        nombre = request.form.get("nombre", "").strip()
        email = request.form.get("email", "").strip().lower()
        password_raw = request.form.get("password", "")
        rol = request.form.get("rol", ROLE_VIEWER).strip()

        if rol not in {ROLE_EDITOR, ROLE_VIEWER}:
            flash("Selecciona un rol valido para el empleado.", "error")
            return redirect(url_for("usuarios"))

        if not nombre or not email or not password_raw:
            flash("Nombre, correo y contrasena son obligatorios.", "error")
            return redirect(url_for("usuarios"))

        existe = Usuario.query.filter_by(email=email).first()
        if existe:
            flash("Ese correo ya esta registrado.", "error")
            return redirect(url_for("usuarios"))

        nuevo = Usuario(
            nombre=nombre,
            email=email,
            password=generate_password_hash(password_raw),
            empresa_id=company_id,
            rol=rol,
            activo=True,
        )
        db.session.add(nuevo)
        db.session.commit()
        flash("Empleado creado correctamente.", "success")
        return redirect(url_for("usuarios"))

    empleados = (
        Usuario.query.filter_by(empresa_id=company_id).order_by(Usuario.id.asc()).all()
    )
    return render_template("usuarios.html", empleados=empleados)


@app.route("/usuarios/<int:id>/rol", methods=["POST"])
@login_required
def actualizar_rol_usuario(id):
    company_required()
    require_admin_permission()

    usuario = get_user_for_current_company_or_404(id)
    nuevo_rol = request.form.get("rol", "").strip()

    if usuario.id == current_user.id:
        flash("No puedes cambiar tu propio rol desde este panel.", "error")
        return redirect(url_for("usuarios"))

    if usuario.rol == ROLE_ADMIN:
        flash("El rol del administrador principal no se cambia desde aqui.", "error")
        return redirect(url_for("usuarios"))

    if nuevo_rol not in {ROLE_EDITOR, ROLE_VIEWER}:
        flash("Selecciona un rol valido.", "error")
        return redirect(url_for("usuarios"))

    usuario.rol = nuevo_rol
    db.session.commit()
    flash("Rol actualizado correctamente.", "success")
    return redirect(url_for("usuarios"))


@app.route("/usuarios/<int:id>/estado", methods=["POST"])
@login_required
def actualizar_estado_usuario(id):
    company_required()
    require_admin_permission()

    usuario = get_user_for_current_company_or_404(id)

    if usuario.id == current_user.id:
        flash("No puedes desactivar tu propia cuenta desde este panel.", "error")
        return redirect(url_for("usuarios"))

    if usuario.rol == ROLE_ADMIN:
        flash("La cuenta principal no se activa ni desactiva desde aqui.", "error")
        return redirect(url_for("usuarios"))

    usuario.activo = not usuario.activo
    db.session.commit()
    flash(
        "Usuario activado correctamente."
        if usuario.activo
        else "Usuario desactivado correctamente.",
        "success",
    )
    return redirect(url_for("usuarios"))


@app.route("/usuarios/<int:id>/password", methods=["POST"])
@login_required
def actualizar_password_usuario(id):
    company_required()
    require_admin_permission()

    usuario = get_user_for_current_company_or_404(id)
    nueva_password = request.form.get("password", "")

    if usuario.rol == ROLE_ADMIN:
        flash("La cuenta principal no cambia su contrasena desde este panel.", "error")
        return redirect(url_for("usuarios"))

    if len(nueva_password) < 6:
        flash("La nueva contrasena debe tener al menos 6 caracteres.", "error")
        return redirect(url_for("usuarios"))

    usuario.password = generate_password_hash(nueva_password)
    db.session.commit()
    flash("Contrasena restablecida correctamente.", "success")
    return redirect(url_for("usuarios"))


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if user_is_superadmin(current_user):
            return redirect(url_for("superadmin_empresas"))
        return redirect(url_for("index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and check_password_hash(usuario.password, password):
            if not usuario.activo:
                flash(
                    "Esta cuenta esta desactivada. Contacta al administrador de tu empresa.",
                    "error",
                )
                return redirect(url_for("login"))

            if usuario.rol == ROLE_SUPERADMIN:
                session.pop("superadmin_company_id", None)
                login_user(usuario)
                flash("Bienvenido.", "success")
                return redirect(url_for("superadmin_empresas"))

            if not usuario.empresa or not usuario.empresa.activo:
                flash("La empresa asociada a esta cuenta no esta activa.", "error")
                return redirect(url_for("login"))

            if usuario.empresa.estado != STATUS_ACTIVE:
                flash("La empresa no tiene acceso habilitado en este momento.", "error")
                return redirect(url_for("login"))

            if usuario.rol not in VALID_ROLES:
                flash("La cuenta no tiene un rol valido configurado.", "error")
                return redirect(url_for("login"))

            login_user(usuario)
            flash("Bienvenido.", "success")
            next_url = request.args.get("next")
            return redirect(next_url or url_for("index"))

        flash("Credenciales invalidas.", "error")

    return render_template("login.html")


@app.route("/logout")
@login_required
def logout():
    session.pop("superadmin_company_id", None)
    logout_user()
    flash("Sesion cerrada.", "success")
    return redirect(url_for("login"))


@app.errorhandler(403)
def forbidden(_error):
    return render_template("403.html"), 403


@app.errorhandler(404)
def not_found(_error):
    return render_template("404.html"), 404


def initialize_database() -> None:
    db.create_all()

    inspector = db.inspect(db.engine)
    columnas_empresa = {col["name"] for col in inspector.get_columns("empresa")}
    if "estado" not in columnas_empresa:
        with db.engine.begin() as connection:
            connection.exec_driver_sql(
                f"ALTER TABLE empresa ADD COLUMN estado VARCHAR(20) NOT NULL DEFAULT '{STATUS_ACTIVE}'"
            )

    columnas_usuario = {col["name"] for col in inspector.get_columns("usuario")}
    if "activo" not in columnas_usuario:
        with db.engine.begin() as connection:
            connection.exec_driver_sql(
                "ALTER TABLE usuario ADD COLUMN activo BOOLEAN NOT NULL DEFAULT 1"
            )

    superadmin = Usuario.query.filter_by(rol=ROLE_SUPERADMIN).first()
    if not superadmin:
        empresa_dummy = Empresa.query.filter_by(slug=INTERNAL_COMPANY_SLUG).first()
        if not empresa_dummy:
            empresa_dummy = Empresa(
                nombre="Plataforma Interna",
                slug=INTERNAL_COMPANY_SLUG,
                estado=STATUS_ACTIVE,
                activo=True,
            )
            db.session.add(empresa_dummy)
            db.session.flush()

        superadmin = Usuario(
            nombre=SUPERADMIN_NAME,
            email=SUPERADMIN_EMAIL,
            password=generate_password_hash(SUPERADMIN_PASSWORD),
            rol=ROLE_SUPERADMIN,
            activo=True,
            empresa_id=empresa_dummy.id,
        )
        db.session.add(superadmin)
        db.session.commit()


with app.app_context():
    initialize_database()


if __name__ == "__main__":
    app.run(debug=True)

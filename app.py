from flask import Flask, render_template, request, redirect
from flask_sqlalchemy import SQLAlchemy
import uuid
import os
import base64
from werkzeug.utils import secure_filename

from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image,PageBreak
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.platypus import PageBreak

from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)

app.secret_key = "clave_secreta"

login_manager = LoginManager()
login_manager.init_app(app)

login_manager.login_view = "login"

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventario.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

UPLOAD_FOLDER = "static/uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

db = SQLAlchemy(app)


# -----------------------------
# TABLA INMUEBLES
# -----------------------------
class Inmueble(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    direccion = db.Column(db.String(200))
    propietario = db.Column(db.String(200))
    fecha_recepcion = db.Column(db.String(50))
    usuario_id = db.Column(db.Integer, db.ForeignKey("usuario.id"))

    inventarios = db.relationship("Inventario", backref="inmueble", lazy=True)


# -----------------------------
# TABLA INVENTARIOS
# -----------------------------
class Inventario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inmueble_id = db.Column(db.Integer, db.ForeignKey("inmueble.id"))
    nombre = db.Column(db.String(200))
    fecha = db.Column(db.String(50))
    token = db.Column(db.String(100), unique=True)

    secciones = db.relationship("Seccion", backref="inventario", lazy=True)


# -----------------------------
# TABLA SECCIONES
# -----------------------------
class Seccion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inventario_id = db.Column(db.Integer, db.ForeignKey("inventario.id"))
    nombre = db.Column(db.String(100))

    fotos = db.relationship("Foto", backref="seccion", lazy=True)
    observaciones = db.relationship("Observacion", backref="seccion", lazy=True)


# -----------------------------
# TABLA FOTOS
# -----------------------------
class Foto(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seccion_id = db.Column(db.Integer, db.ForeignKey("seccion.id"))
    archivo = db.Column(db.String(200))


# -----------------------------
# TABLA OBSERVACIONES
# -----------------------------
class Observacion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    seccion_id = db.Column(db.Integer, db.ForeignKey("seccion.id"))
    comentario = db.Column(db.Text)

##

class Usuario(UserMixin, db.Model):

    id = db.Column(db.Integer, primary_key=True)

    nombre = db.Column(db.String(100))

    email = db.Column(db.String(100), unique=True)

    password = db.Column(db.String(200))

    inmuebles = db.relationship("Inmueble", backref="usuario", lazy=True)
    

# -----------------------------
# PAGINA PRINCIPAL
# -----------------------------
@app.route("/")
def index():

    total_inmuebles = Inmueble.query.count()
    total_inventarios = Inventario.query.count()
    total_fotos = Foto.query.count()

    inmuebles = Inmueble.query.all()

    return render_template(
        "index.html",
        total_inmuebles=total_inmuebles,
        total_inventarios=total_inventarios,
        total_fotos=total_fotos,
        inmuebles=inmuebles
    )

# -----------------------------
# CREAR INMUEBLE
# -----------------------------
@app.route("/crear", methods=["POST"])
@login_required
def crear():

    direccion = request.form["direccion"]
    propietario = request.form["propietario"]
    fecha = request.form["fecha"]

    nuevo = Inmueble(
        direccion=direccion,
        propietario=propietario,
        fecha_recepcion=fecha,
        usuario_id=current_user.id
    )

    db.session.add(nuevo)
    db.session.commit()

    return redirect("/")

# -----------------------------
# VER INMUEBLE
# -----------------------------
@app.route("/inmueble/<int:id>")
def ver_inmueble(id):

    inmueble = Inmueble.query.get_or_404(id)
    inventarios = Inventario.query.filter_by(inmueble_id=id).all()

    return render_template(
        "inmueble.html",
        inmueble=inmueble,
        inventarios=inventarios
    )


# -----------------------------
# CREAR INVENTARIO
# -----------------------------
@app.route("/crear_inventario/<int:id>", methods=["POST"])
def crear_inventario(id):

    nombre = request.form["nombre"]
    fecha = request.form["fecha"]

    nuevo = Inventario(
        inmueble_id=id,
        nombre=nombre,
        fecha=fecha,
        token=str(uuid.uuid4())
    )

    db.session.add(nuevo)
    db.session.commit()

    secciones = ["Sala", "Cocina", "Comedor", "Habitación", "Baño", "Exterior"]

    for s in secciones:
        nueva = Seccion(
            inventario_id=nuevo.id,
            nombre=s
        )
        db.session.add(nueva)

    db.session.commit()

    return redirect(f"/inmueble/{id}")


# -----------------------------
# VER INVENTARIO
# -----------------------------
@app.route("/inventario/<int:id>")
def ver_inventario(id):

    inventario = Inventario.query.get_or_404(id)
    secciones = Seccion.query.filter_by(inventario_id=id).all()

    return render_template(
        "inventario.html",
        inventario=inventario,
        secciones=secciones
    )


# -----------------------------
# VER SECCION
# -----------------------------
@app.route("/seccion/<int:id>")
def ver_seccion(id):

    seccion = Seccion.query.get_or_404(id)

    fotos = Foto.query.filter_by(seccion_id=id).all()
    observaciones = Observacion.query.filter_by(seccion_id=id).all()

    inventario_id = seccion.inventario_id

    return render_template(
        "seccion.html",
        seccion=seccion,
        fotos=fotos,
        observaciones=observaciones,
        inventario_id=inventario_id
    )

# -----------------------------
# SUBIR FOTO / VIDEO
# -----------------------------
@app.route("/subir_foto/<int:id>", methods=["POST"])
def subir_foto(id):

    archivos = request.files.getlist("fotos")

    for archivo in archivos:

        if archivo.filename == "":
            continue

        nombre_archivo = secure_filename(archivo.filename)

        ruta = os.path.join(app.config["UPLOAD_FOLDER"], nombre_archivo)

        archivo.save(ruta)

        nueva = Foto(
            seccion_id=id,
            archivo=nombre_archivo
        )

        db.session.add(nueva)

    db.session.commit()

    return redirect(f"/seccion/{id}")

# -----------------------------
# CREAR OBSERVACION
# -----------------------------
@app.route("/crear_observacion/<int:id>", methods=["POST"])
def crear_observacion(id):

    comentario = request.form["comentario"]

    nueva = Observacion(
        seccion_id=id,
        comentario=comentario
    )

    db.session.add(nueva)
    db.session.commit()

    return redirect(f"/seccion/{id}")

# -----------------------------
# CREAR SECCION MANUAL
# -----------------------------
@app.route("/crear_seccion/<int:id>", methods=["POST"])
def crear_seccion(id):

    nombre = request.form["nombre"]

    nueva = Seccion(
        inventario_id=id,
        nombre=nombre
    )

    db.session.add(nueva)
    db.session.commit()

    return redirect(f"/inventario/{id}")

# -----------------------------
# ELIMINAR SECCION
# -----------------------------
@app.route("/eliminar_seccion/<int:id>")
def eliminar_seccion(id):

    seccion = Seccion.query.get_or_404(id)

    inventario_id = seccion.inventario_id

    db.session.delete(seccion)
    db.session.commit()

    return redirect(f"/inventario/{inventario_id}")

# -----------------------------
# EDITAR SECCION
# -----------------------------
@app.route("/editar_seccion/<int:id>", methods=["GET","POST"])
def editar_seccion(id):

    seccion = Seccion.query.get_or_404(id)

    if request.method == "POST":

        seccion.nombre = request.form["nombre"]

        db.session.commit()

        return redirect(f"/inventario/{seccion.inventario_id}")

    return render_template("editar_seccion.html", seccion=seccion)

# -----------------------------
# TABLA FIRMAS
# -----------------------------
class Firma(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inventario_id = db.Column(db.Integer)
    nombre = db.Column(db.String(200))
    imagen = db.Column(db.Text)

# -----------------------------
# GUARDAR FIRMA
# -----------------------------
@app.route("/guardar_firma/<int:id>", methods=["POST"])
def guardar_firma(id):

    nombre = request.form["nombre"]
    imagen = request.form["firma"]

    nueva = Firma(
        inventario_id=id,
        nombre=nombre,
        imagen=imagen
    )

    db.session.add(nueva)
    db.session.commit()

    return redirect(f"/inventario/{id}")

# -----------------------------
# GENERAR PDF
# -----------------------------
@app.route("/inventario_pdf/<int:id>")
def inventario_pdf(id):

    inventario = Inventario.query.get_or_404(id)
    inmueble = Inmueble.query.get(inventario.inmueble_id)

    secciones = Seccion.query.filter_by(inventario_id=id).all()

    nombre_pdf = f"inventario_{id}.pdf"
    ruta_pdf = os.path.join("static", nombre_pdf)

    styles = getSampleStyleSheet()
    elementos = []

    # LOGO
    logo = "static/logo.png"

    if os.path.exists(logo):
        elementos.append(Image(logo, width=120, height=60))

    elementos.append(Spacer(1,10))

    # ENCABEZADO
    elementos.append(Paragraph("INVENTARIO DE ENTREGA DE INMUEBLE", styles['Title']))
    elementos.append(Spacer(1,20))

    # DATOS DEL INMUEBLE
    elementos.append(Paragraph(f"<b>Dirección:</b> {inmueble.direccion}", styles['BodyText']))
    elementos.append(Paragraph(f"<b>Propietario:</b> {inmueble.propietario}", styles['BodyText']))
    elementos.append(Paragraph(f"<b>Fecha de recepción:</b> {inmueble.fecha_recepcion}", styles['BodyText']))
    elementos.append(Spacer(1,20))

    # SECCIONES
    for s in secciones:

        elementos.append(Paragraph(f"Sección: {s.nombre}", styles['Heading2']))
        elementos.append(Spacer(1,10))

        fotos = Foto.query.filter_by(seccion_id=s.id).all()
        observaciones = Observacion.query.filter_by(seccion_id=s.id).all()

        # FOTOS
        for f in fotos:

            ruta_archivo = os.path.join("static/uploads", f.archivo)

            if os.path.exists(ruta_archivo):

                if f.archivo.lower().endswith(('.jpg','.jpeg','.png')):

                    elementos.append(Image(ruta_archivo, width=350, height=220))
                    elementos.append(Spacer(1,10))

                else:

                    elementos.append(Paragraph("Video adjunto en inventario", styles['BodyText']))
                    elementos.append(Spacer(1,10))

        # OBSERVACIONES
        for o in observaciones:

            elementos.append(Paragraph(f"Observación: {o.comentario}", styles['BodyText']))
            elementos.append(Spacer(1,10))

        elementos.append(Spacer(1,20))

    # PAGINA DE FIRMAS
    elementos.append(PageBreak())

    elementos.append(Paragraph("Firmas del Inventario", styles['Title']))
    elementos.append(Spacer(1,40))

    firmas = Firma.query.filter_by(inventario_id=id).all()

    for firma in firmas:

        elementos.append(Paragraph(f"Firmado por: {firma.nombre}", styles['BodyText']))
        elementos.append(Spacer(1,10))

        imagen_base64 = firma.imagen.split(",")[1]
        imagen_bytes = base64.b64decode(imagen_base64)

        ruta_firma = f"static/firma_{firma.id}.png"

        with open(ruta_firma, "wb") as f:
            f.write(imagen_bytes)

        elementos.append(Image(ruta_firma, width=250, height=120))
        elementos.append(Spacer(1,30))

    # CREAR PDF
    pdf = SimpleDocTemplate(ruta_pdf)
    pdf.build(elementos)

    return redirect(f"/static/{nombre_pdf}")

# -----------------------------
# LINK PUBLICO INVENTARIO
# -----------------------------
@app.route("/publico/<token>")
def inventario_publico(token):

    inventario = Inventario.query.filter_by(token=token).first_or_404()

    secciones = Seccion.query.filter_by(inventario_id=inventario.id).all()

    return render_template(
        "inventario_publico.html",
        inventario=inventario,
        secciones=secciones
    )
####
###
@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

####
@app.route("/registro", methods=["GET","POST"])
def registro():

    if request.method == "POST":

        nombre = request.form["nombre"]
        email = request.form["email"]
        password = generate_password_hash(request.form["password"])

        nuevo = Usuario(
            nombre=nombre,
            email=email,
            password=password
        )

        db.session.add(nuevo)
        db.session.commit()

        return redirect("/login")

    return render_template("registro.html")



###
@app.route("/login", methods=["GET","POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        usuario = Usuario.query.filter_by(email=email).first()

        if usuario and check_password_hash(usuario.password, password):

            login_user(usuario)

            return redirect("/")

    return render_template("login.html")

###
@app.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect("/login")


# -----------------------------
# CREAR BASE DE DATOS
# -----------------------------
with app.app_context():
    db.create_all()


# -----------------------------
# INICIAR SERVIDOR
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
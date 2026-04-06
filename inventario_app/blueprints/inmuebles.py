from flask import Blueprint, render_template
from flask_login import login_required

from ..models import Inventario
from ..services.access import get_inmueble_for_current_company_or_404


bp = Blueprint("inmuebles", __name__)


@bp.route("/inmueble/<int:id>", endpoint="ver_inmueble")
@login_required
def ver_inmueble(id):
    inmueble = get_inmueble_for_current_company_or_404(id)
    inventarios = (
        Inventario.query.filter_by(inmueble_id=id).order_by(Inventario.id.desc()).all()
    )
    return render_template("inmueble.html", inmueble=inmueble, inventarios=inventarios)

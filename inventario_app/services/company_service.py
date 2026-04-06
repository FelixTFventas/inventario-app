from ..models import Empresa
from ..utils.text import slugify


def unique_company_slug(name: str) -> str:
    base_slug = slugify(name)
    slug = base_slug
    counter = 2
    while Empresa.query.filter_by(slug=slug).first():
        slug = f"{base_slug}-{counter}"
        counter += 1
    return slug

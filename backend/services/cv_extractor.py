from io import BytesIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

MAX_CV_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_CV_PAGES = 30
MAX_CV_TEXT_CHARS = 12000


def extract_pdf_text(contents: bytes) -> str:
    if not contents.startswith(b'%PDF-'):
        raise ValueError('Le fichier transmis n’est pas un PDF valide.')
    if len(contents) > MAX_CV_UPLOAD_BYTES:
        raise ValueError('Le PDF dépasse la taille maximale de 5 Mo.')

    try:
        reader = PdfReader(BytesIO(contents), strict=False)
        if reader.is_encrypted:
            raise ValueError('Les PDF protégés par mot de passe ne sont pas pris en charge.')
        if len(reader.pages) > MAX_CV_PAGES:
            raise ValueError(f'Le PDF ne peut pas dépasser {MAX_CV_PAGES} pages.')
        text = '\n'.join(page.extract_text() or '' for page in reader.pages)
    except PdfReadError as error:
        raise ValueError('Le PDF est illisible ou endommagé.') from error

    extracted = text.strip()
    if not extracted:
        raise ValueError('Aucun texte exploitable n’a été trouvé dans le PDF.')
    return extracted[:MAX_CV_TEXT_CHARS]

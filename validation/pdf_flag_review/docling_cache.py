"""Reuse Docling's layout-model output between flag-review runs.

Docling is the slow step of the PDF pipeline (minutes per long paper on CPU). Its output for
a given PDF does not change when AnomalyNerd's parser or detectors change, so the review
script can save it once and reload it. Everything after Docling (table assessment, tidying,
detectors, scoring) still runs for real.

The cache key is the PDF's SHA-256, the docling and docling-core versions, and the source of
pdf_ingest._try_docling (which sets the Docling options). If any of these change, the PDF is
converted again. detector_dir() gives the folder for saved detector results. Only the review
script uses these caches; the tool itself never reads them.
"""
import hashlib
import importlib.metadata
import inspect
import os


def _sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def enable(cache_dir):
    """Make every Docling conversion in this process read from / write to cache_dir."""
    from docling.document_converter import DocumentConverter
    from docling_core.types.doc import DoclingDocument
    from anomalynerd import pdf_ingest

    os.makedirs(cache_dir, exist_ok=True)
    versions = "|".join(importlib.metadata.version(p) for p in ("docling", "docling-core"))
    options = hashlib.sha256(inspect.getsource(pdf_ingest._try_docling).encode()).hexdigest()[:12]
    original = DocumentConverter.convert

    class _Result:
        def __init__(self, document):
            self.document = document

    def convert(self, source, *args, **kwargs):
        path = str(source)
        if not os.path.isfile(path):
            return original(self, source, *args, **kwargs)
        key = hashlib.sha256(f"{_sha256(path)}|{versions}|{options}".encode()).hexdigest()[:24]
        cached = os.path.join(cache_dir, key + ".json")
        if os.path.exists(cached):
            return _Result(DoclingDocument.load_from_json(cached))
        result = original(self, source, *args, **kwargs)
        tmp = cached + ".tmp"
        result.document.save_as_json(tmp)
        os.replace(tmp, cached)
        return result

    DocumentConverter.convert = convert


def detector_dir(cache_dir):
    """Folder for the detector checkpoints (anomalynerd.bounded). bounded keys each result on
    the detector source and the table; the folder name adds model.py and ingest.py, which the
    detectors import, so a change there also starts fresh."""
    import anomalynerd
    root = os.path.dirname(anomalynerd.__file__)
    h = hashlib.sha256()
    for name in ("model.py", "ingest.py"):
        with open(os.path.join(root, name), "rb") as f:
            h.update(f.read())
    return os.path.join(cache_dir, "detectors-" + h.hexdigest()[:12])

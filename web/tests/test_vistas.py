import pytest

from app.vistas import titulo_legible


@pytest.mark.parametrize("original, legible", [
    ("FORMULARIOS GENERALES", "Formularios Generales"),
    ("MANUALES Y DOCUMENTACIÓN NEOSTAR", "Manuales y Documentación Neostar"),
    ("POLITICAS DE PREVENCIÓN DEL LAVADO DE ACTIVOS (UIF)", "Politicas de Prevención del Lavado de Activos (UIF)"),
    ("KIA SANTA FE - PV", "KIA Santa Fe - PV"),
    ("IN -ADMINISTRACIÓN", "IN - Administración"),
    ("IN - ADMINISTRACIÓN - ALCO ROSARIO S.A", "IN - Administración - Alco Rosario S.A"),
    ("CICLOS DE VIDA - ASPECTOS E IMPACTOS AMBIENTALES", "Ciclos de Vida - Aspectos e Impactos Ambientales"),
    ("PROTOCOLOS DE SEGURIDAD FRENTE AL COVID-19", "Protocolos de Seguridad Frente al Covid-19"),
    ("CONTROLES OP SANTA FE", "Controles OP Santa Fe"),
    ("CAÑADA", "Cañada"),
    ("SGI", "SGI"),
    ("BYD", "BYD"),
    ("2018", "2018"),
    ("DE PRUEBA", "De Prueba"),  # la primera palabra siempre con mayúscula
    # Si ya tiene minúsculas se respeta tal cual
    ("Analisis de Ciclo de Vida - Talleres", "Analisis de Ciclo de Vida - Talleres"),
])
def test_titulo_legible(original, legible):
    assert titulo_legible(original) == legible

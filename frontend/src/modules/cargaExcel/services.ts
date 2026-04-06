export async function getAreas() {
  const res = await fetch("/api/catalogos/areas/");
  return res.json();
}

export async function getTemas(idArea: number) {
  const res = await fetch(`/api/catalogos/temas/?id_area=${idArea}`);
  return res.json();
}

export async function getDiccionario(idTema: number) {
  const res = await fetch(`/api/catalogos/diccionario/?id_tema=${idTema}`);
  return res.json();
}
export async function subirExcel(idTema: number, archivo: File, hoja: string) {
  const formData = new FormData();
  formData.append("id_tema", idTema.toString());
  formData.append("file", archivo);
  formData.append("hoja", hoja);

  const resp = await fetch("/api/catalogos/subir_excel/", {
    method: "POST",
    body: formData,
  });

  const data = await resp.json();

  if (!resp.ok) {
    throw data;
  }

  return data;
}

export async function obtenerHojas(archivo: File) {
  const formData = new FormData();
  formData.append("file", archivo);

  const resp = await fetch("/api/catalogos/obtener_hojas_excel/", {
    method: "POST",
    body: formData,
  });

  return resp.json();
}

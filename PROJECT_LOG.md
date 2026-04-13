# Project Log

Este documento recoge **problemas, decisiones técnicas y avances relevantes**
durante la construcción del proyecto.

El objetivo es **documentar el razonamiento del equipo**, no solo el resultado final.

---

## 📅 Entrada #001 – Inicio del proyecto

**Fecha:**  13/04/2026
**Autores:**  Grupo

### Contexto
Ingesta del dataset a S3

### Decisiones tomadas
- Decisión 1: Copiar la ARN del dataset https://registry.opendata.aws/amazon-reviews-ml/ al bucket de S3
- Decisión 2: Copiar dataset de Kaggle https://www.kaggle.com/datasets/mexwell/amazon-reviews-multi/data al s3

### Problemas
- Problemas para copiar el dataset original al S3 por falta de permiso.

### Resultado

---

### Logs relevantes
```text

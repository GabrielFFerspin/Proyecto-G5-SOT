# Project Log – Knowledge Assistant (RAG + Neo4j + Amazon Bedrock)

Este documento recoge **problemas, decisiones técnicas y avances relevantes**
durante la construcción del proyecto.

El objetivo es **documentar el razonamiento del equipo**, no solo el resultado final.

---

## 📅 Entrada #001 – Inicio del proyecto

**Fecha:** 13/04/2026  
**Autores:** Grupo 5

### Contexto
Ingesta del dataset a S3. El enunciado recomienda el dataset público de
Amazon Reviews disponible en el Registry of Open Data on AWS.

### Decisiones tomadas
- Intentar copiar la ARN del dataset original:
  `https://registry.opendata.aws/amazon-reviews-ml/`
- Tras comprobar que estaba deprecado, se cambió la fuente de ingesta.
- Se descargó el dataset desde Kaggle:
  `https://www.kaggle.com/datasets/mexwell/amazon-reviews-multi/data`
- Se subió manualmente al bucket de S3.

### Problemas
- El dataset original del Registry of Open Data on AWS estaba **deprecado**
  y no era accesible mediante ARN directa.

### Resultado
- Dataset disponible en S3 desde fuente alternativa (Kaggle).
- Subset utilizado: reviews en inglés (`reviews_en.csv`).

---

## 📅 Entrada #002 – Creación de la VPC e IAM

**Fecha:** 13/04/2026  
**Autores:** Grupo 5

### Contexto
Creación de la red privada (VPC) e identidades de acceso (IAM) para
aislar los recursos del proyecto y controlar permisos entre servicios.

### Decisiones tomadas
- Definir rango de IPs propio (`10.0.0.0/16`) para aislar el proyecto.
- Crear subnets públicas y privadas dentro de la VPC.
- Crear roles IAM para Lambda (permisos de Bedrock, logs) y Glue
  (permisos de S3 y Neo4j).
- Toda la configuración definida mediante **CloudFormation** (IaC).

### Justificación técnica
- La VPC aísla Neo4j y el backend del resto de la cuenta AWS.
- IAM garantiza el **principio de mínimo privilegio**:
  cada servicio solo tiene los permisos que necesita.
- Evita credenciales hardcodeadas en el código.

### Problemas
- Sin incidencias en esta fase.

### Resultado
- VPC operativa con subnets definidas.
- Roles IAM creados y asignados a Lambda y Glue.

---

## 📅 Entrada #003 – Creación de la EC2 y problemas de conectividad

**Fecha:** 13/04/2026  
**Autores:** Grupo 5

### Contexto
Creación de una instancia EC2 con Ubuntu para alojar Neo4j,
tal como exige el enunciado.

### Decisiones tomadas
- Sistema operativo: **Ubuntu**.
- Instalación de Neo4j planificada mediante **UserData** en CloudFormation
  (sin configuración manual).
- Definición del Security Group para puertos Bolt (7687) y Browser (7474).

### Problemas
- **No fue posible conectar a la EC2 por SSH.**
  - No se podía crear ni asociar un **Internet Gateway** por falta de permisos.
  - Sin IGW, la instancia no tenía ruta a Internet.
- **No fue posible verificar Neo4j** dentro de la instancia.

### Análisis
- SSH requiere:
  1. IP pública o ruta a Internet (Internet Gateway).
  2. Security Group con puerto 22 abierto.
  3. Key Pair válido.
  4. Permisos para asociar el IGW.
- La cuenta AWS del entorno **no permite crear Internet Gateways**.

### Decisión tomada
- Se descartó SSH como mecanismo de acceso.
- Se usó **Neo4j Desktop en local** para desarrollo y demo.

### Justificación técnica
- SSH introduce configuración manual no reproducible.
- El enunciado exige IaC, no acceso interactivo.
- En entornos reales, Neo4j se administra sin acceso SSH directo.
- Neo4j Desktop es funcionalmente idéntico para desarrollo y demo.

### Resultado
- Desarrollo y demo con **Neo4j Desktop local**.

### Logs relevantes
```text
Error: Unable to create Internet Gateway – insufficient permissions
SSH connection timeout – no route to host
````

***

## 📅 Entrada #004 – Creación del grafo en Neo4j

**Fecha:** 14/04/2026  
**Autores:** Grupo 5

### Contexto

Ingesta del dataset de reviews en Neo4j Desktop y construcción del
modelo de grafo según el enunciado:

*   Nodos: `Customer`, `Product`, `Review`
*   Relaciones: `PURCHASED`, `WROTE`, `ABOUT`, `SIMILAR_TO`

***

### Problema A – Error 22N43: `Could not load external resource`

**Síntoma**

```text
22N43: Could not load external resource from file:///reviews.csv
```

**Causa raíz**

*   El CSV estaba en `tools/import`, que Neo4j **ignora completamente**.
*   Neo4j Desktop solo permite `LOAD CSV` desde la carpeta `import`
    asociada al motor de la base de datos.

**Solución**

*   Acceder a la carpeta correcta:
    Neo4j Desktop → Base de datos → `⋮` → Open Folder → Import
*   Copiar `reviews_en.csv` únicamente en esa carpeta.

**Aprendizaje**

> Neo4j solo permite `LOAD CSV` desde su carpeta `import` oficial,
> por razones de seguridad.

***

### Problema B – Error 22NAC: `characters after an ending quote`

**Síntoma**

```text
22NAC: Data exception - characters after an ending quote in a CSV field
```

**Causa raíz**

*   El dataset contenía texto libre con:
    *   Comillas sin escapar.
    *   Saltos de línea dentro de campos.
    *   Filas malformadas (no conformes con RFC 4180).
*   Neo4j es **muy estricto** con el estándar CSV.

**Primer intento (insuficiente)**

```python
df["review_body"] = df["review_body"].str.replace('"', '""')
df.to_csv("reviews_clean.csv", quoting=1)
```

El error persistió porque seguían existiendo filas corruptas.

**Solución definitiva – Conversión a TSV**

*   Se abandonó el formato CSV con comillas.
*   Se creó un pipeline de limpieza en Python:

```python
import pandas as pd
import csv

df = pd.read_csv("reviews_en.csv", engine="python", on_bad_lines="skip")

text_cols = ["review_title", "review_body"]
for c in text_cols:
    df[c] = (df[c].astype(str)
                  .str.replace("\r\n", " ", regex=False)
                  .str.replace("\n",   " ", regex=False)
                  .str.replace("\r",   " ", regex=False)
                  .str.replace("\t",   " ", regex=False)
                  .str.replace('"',    "",  regex=False))

df.to_csv("reviews_neo4j.tsv", sep="\t", index=False,
          quoting=csv.QUOTE_NONE, escapechar="\\")
```

**Carga en Neo4j**

```cypher
LOAD CSV WITH HEADERS
FROM 'file:///reviews_neo4j.tsv' AS row
FIELDTERMINATOR '\t'
RETURN row
LIMIT 5;
```

**Resultado:** ✅ Sin errores 22NAC ni 22N43.

**Justificación técnica**

> TSV elimina ambigüedades con comillas en texto libre.
> Es una práctica habitual en pipelines de datos reales.

***

### Problema C – Advertencias 01N51 / 01N52

**Síntoma**

```text
01N51: Relationship type `SIMILAR_TO` does not exist
01N52: Property key `weight` does not exist
```

**Causa raíz**

*   Neo4j es schema-less: tipos de relación y propiedades
    se crean dinámicamente.
*   Las advertencias aparecen al hacer `MATCH` sobre algo
    que aún no existe.

**Solución**

*   No se realizó ninguna acción.
*   Tras crear `SIMILAR_TO`, las advertencias desaparecieron.

**Conclusión**

> Son **warnings informativos**, no errores.

***

### Problema D – `REMOVE` sin cambios

**Síntoma**

```text
No changes, no records
```

**Causa raíz**

*   Las propiedades a eliminar nunca existieron en los nodos.
*   Neo4j no almacena propiedades nulas.
*   `Database Information` muestra historial de esquema,
    no el estado real de cada nodo.

**Conclusión**

> El grafo estaba ya limpio y consistente. `REMOVE` es idempotente.

***

### Resultado final – Modelo del grafo

**Nodos**

| Nodo       | Propiedades                                       |
| ---------- | ------------------------------------------------- |
| `Customer` | `reviewer_id`                                     |
| `Product`  | `product_id`, `category`                          |
| `Review`   | `review_id`, `stars`, `title`, `body`, `language` |

**Relaciones**

| Relación                                        | Descripción           |
| ----------------------------------------------- | --------------------- |
| `(:Customer)-[:PURCHASED]->(:Product)`          | Compra                |
| `(:Customer)-[:WROTE]->(:Review)`               | Autoría               |
| `(:Review)-[:ABOUT]->(:Product)`                | Review sobre producto |
| `(:Product)-[:SIMILAR_TO {weight}]->(:Product)` | Co-compra             |

**Queries de creación**

```cypher
// Customers
LOAD CSV WITH HEADERS FROM 'file:///reviews_neo4j.tsv' AS row
FIELDTERMINATOR '\t'
MERGE (:Customer {reviewer_id: row.reviewer_id});

// Products
LOAD CSV WITH HEADERS FROM 'file:///reviews_neo4j.tsv' AS row
FIELDTERMINATOR '\t'
MERGE (p:Product {product_id: row.product_id})
SET p.category = row.product_category;

// Reviews
LOAD CSV WITH HEADERS FROM 'file:///reviews_neo4j.tsv' AS row
FIELDTERMINATOR '\t'
MERGE (r:Review {review_id: row.review_id})
SET r.stars    = toInteger(row.stars),
    r.title    = row.review_title,
    r.body     = row.review_body,
    r.language = row.language;

// Relaciones
LOAD CSV WITH HEADERS FROM 'file:///reviews_neo4j.tsv' AS row
FIELDTERMINATOR '\t'
MATCH (c:Customer {reviewer_id: row.reviewer_id})
MATCH (p:Product  {product_id:  row.product_id})
MATCH (r:Review   {review_id:   row.review_id})
MERGE (c)-[:WROTE]->(r)
MERGE (r)-[:ABOUT]->(p)
MERGE (c)-[:PURCHASED]->(p);

// SIMILAR_TO por co-compra
MATCH (c:Customer)-[:PURCHASED]->(p1:Product)
MATCH (c)-[:PURCHASED]->(p2:Product)
WHERE p1.product_id < p2.product_id
WITH p1, p2, COUNT(DISTINCT c) AS common_buyers
MERGE (p1)-[s:SIMILAR_TO]->(p2)
SET s.weight = common_buyers;
```

***


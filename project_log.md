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
- Instalación de Neo4j planificada mediante **UserData** en CloudFormation.
- Definición del Security Group para puertos Bolt (7687) y Browser (7474).

### Problemas
- **No fue posible conectar a la EC2 por SSH.**
  - No se podía crear ni asociar un **Internet Gateway** por falta de permisos.
  - Sin IGW, la instancia no tenía ruta a Internet.
- **No fue posible verificar Neo4j** dentro de la instancia.

### Análisis
- SSH requiere IP pública, Security Group con puerto 22, Key Pair válido y permisos IGW.
- La cuenta AWS del entorno **no permite crear Internet Gateways**.

### Decisión tomada
- Se descartó SSH como mecanismo de acceso.
- Se usó **Neo4j Desktop en local** para desarrollo y demo.

### Justificación técnica
- SSH introduce configuración manual no reproducible.
- El enunciado exige IaC, no acceso interactivo.
- Neo4j Desktop es funcionalmente idéntico para desarrollo y demo.

### Resultado
- Desarrollo y demo con **Neo4j Desktop local**.

### Logs relevantes
```text
Error: Unable to create Internet Gateway – insufficient permissions
SSH connection timeout – no route to host
```

---

## 📅 Entrada #004 – Creación del grafo en Neo4j

**Fecha:** 14/04/2026
**Autores:** Grupo 5

### Contexto
Ingesta del dataset de reviews en Neo4j Desktop y construcción del
modelo de grafo según el enunciado.

### Problema A – Error 22N43: `Could not load external resource`

**Síntoma**
```text
22N43: Could not load external resource from file:///reviews.csv
```

**Causa raíz**
- El CSV estaba en `tools/import`, que Neo4j ignora completamente.
- Neo4j Desktop solo permite `LOAD CSV` desde la carpeta `import` oficial.

**Solución**
- Acceder: Neo4j Desktop → Base de datos → `⋮` → Open Folder → Import
- Copiar `reviews_en.csv` únicamente en esa carpeta.

**Aprendizaje**
> Neo4j solo permite `LOAD CSV` desde su carpeta `import` oficial por razones de seguridad.

---

### Problema B – Error 22NAC: `characters after an ending quote`

**Síntoma**
```text
22NAC: Data exception - characters after an ending quote in a CSV field
```

**Causa raíz**
- Texto libre con comillas sin escapar, saltos de línea y filas malformadas.

**Solución definitiva – Conversión a TSV**

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

**Resultado:** Sin errores 22NAC ni 22N43.

### Resultado final – Modelo del grafo

| Nodo | Propiedades |
|---|---|
| `Customer` | `reviewer_id` |
| `Product` | `product_id`, `category` |
| `Review` | `review_id`, `stars`, `title`, `body`, `language` |

| Relación | Descripción |
|---|---|
| `(:Customer)-[:PURCHASED]->(:Product)` | Compra |
| `(:Customer)-[:WROTE]->(:Review)` | Autoría |
| `(:Review)-[:ABOUT]->(:Product)` | Review sobre producto |
| `(:Product)-[:SIMILAR_TO {weight}]->(:Product)` | Co-compra |

---

## 📅 Entrada #005 – Visualización del grafo y justificación de la Query 1

**Fecha:** 14/04/2026
**Autores:** Grupo 5

### Contexto
Visualización del subgrafo asociado al producto de referencia
(`product_en_0060319 / furniture`) para justificar la elección en la demo.

### Imagen 1 – Co-compra directa

```cypher
MATCH path = (p:Product {product_id: "product_en_0060319"})
             <-[:PURCHASED]-(c:Customer)
             -[:PURCHASED]->(other:Product)
RETURN path;
```

**Resultado:** 3 nodos, 2 relaciones. Confirma co-compras reales entre `furniture` y `home`.

### Imagen 2 – Contexto completo (clientes + reviews)

```cypher
MATCH path = (other:Product)
             <-[:PURCHASED]-(c:Customer)
             -[:PURCHASED]->(p:Product {product_id: "product_en_0060319"})
OPTIONAL MATCH (r:Review)-[:ABOUT]->(p)
OPTIONAL MATCH (c)-[:WROTE]->(r)
RETURN path, r LIMIT 30;
```

**Resultado:** 5 nodos, 6 relaciones. Confirma 2 clientes reales con reviews verificadas.

### Imagen 3 – Relación SIMILAR_TO

```cypher
MATCH path = (p:Product {product_id: "product_en_0060319"})
             <-[:PURCHASED]-(c:Customer)
             -[:PURCHASED]->(other:Product)
OPTIONAL MATCH (p)-[s:SIMILAR_TO]->(sim:Product)
RETURN path, s, sim LIMIT 30;
```

**Resultado:** Relación SIMILAR_TO entre `furniture` y `home` con `weight = 1`.

---

## 📅 Entrada #006 – Remediación de vulnerabilidades de seguridad y decisión de arquitectura Neo4j

**Fecha:** 15/04/2026
**Autores:** Grupo 5

### Problema 1 — Vulnerabilidad CRÍTICA

**Security Group:** `sg-04f257b39c7560a9d` | `neo4j-g5-security`

**Alerta:**
```text
AWS SG insecure critical inbound access rules
Categoría: Native Cloud | Severidad: CRÍTICA
```

**Causa raíz:** Puerto SSH (22) abierto sin restricción de IP (`0.0.0.0/0`).

**Solución:** Eliminada regla SSH del Security Group.

### Problema 2 — Puertos autorizados por política ISD

Puerto 22 (SSH) **explícitamente prohibido** por política de seguridad corporativa.

**Puertos TCP autorizados:** 9000, 53, 80, 8080, 8443, 443, 5061, 5060, 15000-20999.

### Decisión final — Neo4j AuraDB via API Python

| Alternativa | Resultado | Motivo |
|---|---|---|
| SSH (puerto 22) | ❌ | Prohibido por ISD |
| Internet Gateway | ❌ | Sin permisos de red |
| AWS Session Manager | ❌ | Sin permisos en la cuenta |
| Neo4j local (Desktop) | ✅ | Viable para desarrollo |
| **Neo4j AuraDB** | ✅✅ | **Solución definitiva** |

---

## 📅 Entrada #007 – RAG funcionando end-to-end en local

**Fecha:** 15/04/2026
**Autores:** Grupo 5

### Hito alcanzado
Pipeline RAG completamente funcional en local.

### Stack tecnológico
- Grafo: Neo4j Desktop local
- Modelo: eu.amazon.nova-micro-v1:0
- Región: eu-west-3
- Autenticación: IAM via boto3

---

## 📅 Entrada #008 – Integración del motor RAG con Neo4j AuraDB

**Fecha:** 16/04/2026
**Autores:** Grupo 5

### Avances clave
- ✅ Conexión Lambda → Neo4j AuraDB via `neo4j+s` (SSL)
- ✅ Ejecución correcta de queries Cypher desde Lambda
- ✅ Flujo RAG completo: intent → grafo → contexto → Bedrock
- ✅ Autenticación Bedrock mediante IAM (boto3), sin API keys
- ✅ Respuestas coherentes sin alucinaciones

---

## 📅 Entrada #009 – Carga del grafo en Neo4j AuraDB mediante AWS Glue

**Fecha:** 16/04/2026
**Autores:** Grupo 5

### Avances clave
- ✅ Ingesta distribuida desde S3 con Spark en AWS Glue
- ✅ Nodos `Customer`, `Product`, `Review` con constraints de unicidad
- ✅ Relaciones `WROTE`, `PURCHASED`, `ABOUT`, `SIMILAR_TO` con `weight`
- ✅ Escrituras batch en AuraDB
- ✅ Job funcional contra Neo4j AuraDB

---

## 📅 Entrada #010 – Evaluación del esquema del grafo y ajuste de queries

**Fecha:** 16/04/2026
**Autores:** Grupo 5

### Contexto
Evaluación del comportamiento del RAG ante preguntas de afinidad
de co-compra entre categorías sobre el grafo de AuraDB.

### Observaciones
Las queries Cypher se ejecutan sin errores. El sistema responde
correctamente a todas las intenciones definidas.

---

## 📅 Entrada #011 – Validación final del RAG en AWS

**Fecha:** 17/04/2026
**Autores:** Grupo 5

### Hito alcanzado
Pipeline RAG completamente funcional en AWS.

### Preguntas validadas

| Pregunta | Intent | Resultado |
|---|---|---|
| ¿Qué productos se compran juntos habitualmente? | `category_affinity` | 10 pares reales ✅ |
| ¿Cuáles son los productos más populares y mejor valorados? | `top_rated` | 10 productos rating 5.0 ✅ |

### Stack validado
- Dataset: Amazon Reviews 2023 – Toys and Games (92.120 reviews)
- Grafo: Neo4j AuraDB (92.120 nodos, 126.049 relaciones)
- Lambda: Python 3.11
- LLM: Amazon Nova Micro (eu-west-3)
- Auth: IAM + Secrets Manager

---

## 📅 Entrada #012 – Análisis de calidad del dataset original y decisión de cambio

**Fecha:** 17/04/2026
**Autores:** Grupo 5

### Análisis en Neo4j

```cypher
MATCH (c:Customer)-[:PURCHASED]->(p:Product)
WITH c, COUNT(DISTINCT p) AS num_productos
WHERE num_productos > 1
RETURN COUNT(c) AS multi_buyers,
       AVG(num_productos) AS media,
       MAX(num_productos) AS maximo
```

### Resultados

| Métrica | Valor |
|---|---|
| Total clientes | 49.865 |
| Multi-product buyers | 132 |
| Porcentaje | **0,26 %** |
| Máximo productos/cliente | 3 |

### Conclusión
El 99,74 % de los clientes compraron un único producto → señal de co-compra insuficiente.
Se inicia búsqueda de dataset alternativo.

---

## 📅 Entrada #013 – Evaluación de datasets alternativos y selección

**Fecha:** 17/04/2026
**Autores:** Grupo 5

### Datasets evaluados

| Dataset | Fuente | Multi-buyers | % | Decisión |
|---|---|---|---|---|
| Kaggle ML (original) | Kaggle | 132 | 0,26 % | ❌ |
| Amazon Reviews ML (multilingüe) | Kaggle | 80.269 | 7,31 % | ⚠️ |
| All_Beauty McAuley 2023 | HuggingFace | 43.044 | 6,81 % | ❌ |
| Electronics McAuley 2023 | HuggingFace | N/A | ~15 % | ❌ 20 GB |
| **Toys_and_Games McAuley 2023** | **HuggingFace** | **2.834.076** | **34,92 %** | ✅ |

### Justificación de Toys_and_Games
- ✅ 34,92 % multi-buyers → 5x mejor que el anterior
- ✅ Media 9,93 productos/cliente
- ✅ Tamaño manejable (~1-2 GB)
- ✅ Compatible con el ETL existente

### Ajuste al límite AuraDB Free (200K nodos)

| Nodo | Total |
|---|---|
| Review | 49.993 |
| Product | 34.507 |
| Customer | 7.620 |
| **Total** | **92.120** |

---

## 📅 Entrada #014 – Ingesta del nuevo dataset y ajuste del pipeline

**Fecha:** 17/04/2026
**Autores:** Grupo 5

### Avances clave

**A — Descarga y conversión**
- Descarga JSONL desde HuggingFace al vuelo (sin guardar en disco)
- Conversión a TSV eliminando columnas innecesarias
- Fichero: `reviews_toys_games.tsv`

**B — Nuevo Glue Job**

| Error | Causa | Solución |
|---|---|---|
| `No module named 'neo4j'` | Driver no incluido | Subir `.whl` a S3 |
| `ConcurrentRunsExceededException` | Job anterior activo | Esperar finalización |
| `Connection refused` | `--JOB_NAME` duplicado | Eliminar parámetro manual |
| Límite 200K nodos AuraDB | Dataset grande | Reducir a 92.120 reviews |

**C — Verificación final del grafo**
```
SIMILAR_TO: 126.049 relaciones
Peso máximo: 6
Multi-buyers: 4.698 (61,6 %)
Media productos/cliente: 9,93
```

---

## 📅 Entrada #015 – Cambio de dataset a multi-categoría

**Fecha:** 21/04/2026
**Autores:** Grupo 5

### Contexto
Para mejorar la cobertura y la señal de co-compra, se amplió el dataset
de una categoría (Toys_and_Games) a tres categorías:
`Toys_and_Games`, `Sports_and_Outdoors`, `Video_Games`.

### Avances clave
- ✅ Descarga de 3 datasets desde HuggingFace McAuley-Lab/Amazon-Reviews-2023
- ✅ Merge en único fichero `reviews_multi_category_enriched.tsv`
- ✅ Total: **190,750 reseñas · 3 categorías**
- ✅ Enriquecimiento con `product_title` (94.8% cobertura)
- ✅ Filtrado de bots: 15 reviewers eliminados (>500 reseñas y ratio >0.95)
- ✅ Cálculo de **Bayesian Score**: C=10, mean=4.32

### Bayesian Score — Justificación técnica
El score bayesiano penaliza productos con pocas reseñas frente a
productos con muchas reseñas y rating alto:

```
bayesian_score = (C * mean + n * avg_rating) / (C + n)
  C    = 10       (prior — peso de la media global)
  mean = 4.32     (media global del dataset)
  n    = review_count del producto
```

> Ejemplo: Snap Circuits tiene 5.0 estrellas pero solo 19 reviews → score 4.77.
> Mario Kart tiene 4.94 estrellas con 81 reviews → score 4.87. ✅

### Campo cross_cat en CO_PURCHASED
Se añadió el flag `cross_cat: true/false` para identificar
co-compras entre categorías distintas, habilitando el intent
`category_affinity` con datos reales.

---

## 📅 Entrada #016 – Actualización del Glue Job v3 y recarga del grafo

**Fecha:** 21/04/2026
**Autores:** Grupo 5

### Contexto
Con el nuevo dataset multi-categoría, se actualizó el Glue Job
para generar el nuevo esquema del grafo en AuraDB.

### Nuevo esquema del grafo

**Nodos:**

| Nodo | Propiedades |
|---|---|
| `:Product` | product_id, title, category, bayesian_score, avg_stars, review_count |
| `:Reviewer` | reviewer_id, review_count, avg_stars |
| `:Category` | name |

**Relaciones:**

| Relación | Propiedades |
|---|---|
| `REVIEWED` | stars, timestamp, year, bayesian_score |
| `CO_PURCHASED` | weight, cross_cat |
| `BELONGS_TO` | — |
| `ACTIVE_IN` | review_count, avg_stars |

### Estadísticas finales en AuraDB

| Elemento | Total |
|---|---|
| Nodos totales | 150,323 |
| :Product | 107,021 |
| :Reviewer | 43,299 |
| :Category | 3 |
| Relaciones totales | 344,749 |
| CO_PURCHASED | 19,167 |
| REVIEWED | 190,750 |
| BELONGS_TO | 107,021 |
| ACTIVE_IN | 27,831 |

### Problemas resueltos
- **MERGE idempotente**: evita duplicados en recargas sucesivas
- **Batch de 500 registros**: respeta límites de escritura de AuraDB Free
- **cross_cat flag**: calculado comparando `category` de ambos productos

---

## 📅 Entrada #017 – Actualización del pipeline RAG v3

**Fecha:** 21/04/2026
**Autores:** Grupo 5

### Contexto
Adaptación completa del `rag_pipeline.py` al nuevo esquema del grafo
multi-categoría.

### Cambios clave

**6 intents implementados:**

| Intent | Query | Descripción |
|---|---|---|
| `top_rated` | `Q_TOP_RATED` | Top global por bayesian_score |
| `top_by_category` | `Q_TOP_BY_CATEGORY` | Top por :Category {name} |
| `copurchase` | `Q_CO_PURCHASED` | Co-compras con product_id |
| `copurchase` (sin id) | `Q_COPURCHASE_GENERIC` | Co-compras globales |
| `similar_to` | `Q_CO_PURCHASED` | Similares via co-compra |
| `category_affinity` | `Q_CATEGORY_AFFINITY` | CO_PURCHASED cross_cat=true |
| `combined_score` | `Q_COMBINED` | Bayesian + grado co-compra |

### Resultados validados via Postman

| Intent | Resultado destacado |
|---|---|
| `top_rated` | Mario Kart 8 Deluxe (score 4.87, 81 reviews) ✅ |
| `copurchase` | Final Fantasy XV ↔ FF VII Remake (31 co-compras) ✅ |
| `category_affinity` | Toys ↔ Sports (peso total 5,492) ✅ |
| `similar_to` | SanDisk Switch → ecosistema Nintendo completo ✅ |
| `top_by_category` | Snap Circuits Jr. (Toys, score 4.77, 5.0★) ✅ |

---

## 📅 Entrada #018 – Frontend Streamlit y visualización del subgrafo

**Fecha:** 22/04/2026
**Autores:** Grupo 5

### Contexto
Desarrollo del frontend web para la demo final, integrando
la visualización interactiva del subgrafo Neo4j.

### Stack
- **Streamlit** — framework UI
- **pyvis** — visualización de grafos interactivos
- **neo4j-driver** — conexión directa a AuraDB desde Streamlit
- **requests** — llamadas a API Gateway

### Features del frontend

**Tab 1 — Pregunta al Asistente:**
- Input de pregunta con 7 ejemplos de auto-fill
- Llamada a Lambda via API Gateway
- Badges de intent y categoría
- Respuesta Bedrock en caja estilizada
- Expander con contexto Neo4j + subgrafo interactivo

**Tab 2 — Explorar Grafo:**
- 4 métricas del grafo (productos, reviewers, co-compras, reseñas)
- Bar chart de distribución por categoría
- Esquema del grafo en markdown
- Tabla de afinidad entre categorías

**Tab 3 — Top Productos:**
- Top 10 por categoría con bayesian score
- Tabla con score, estrellas y reviews

### Subgrafo interactivo (pyvis)

| Elemento | Estilo |
|---|---|
| :Product | 🔵 Teal (#4ec9b0) · dot · size=20 |
| :Category | 🟠 Naranja (#e67e22) · diamond · size=45 |
| CO_PURCHASED | Teal · grosor = weight (max 10) |
| BELONGS_TO | Naranja · grosor = 1 |

### Problemas resueltos

| Error | Causa | Solución |
|---|---|---|
| `DatabaseNotFound` | AuraDB usa database="e5d261e6" | Pasar `database=NEO4J_DATABASE` explícitamente |
| `Unauthorized` | Credenciales vacías en fallback | Crear `.streamlit/secrets.toml` |
| `render_subgraph() unexpected keyword 'database'` | Fichero antiguo en Codespace | Reescribir `graph_visualizer.py` completo |
| `StreamlitDuplicateElementKey` | Keys de botones repetidas | Usar `key=f"ex_{i}"` con enumerate |

### Deploy
- **Plataforma**: Streamlit Community Cloud
- **Repo**: GabrielFFerspin/Proyecto-G5-SOT
- **Main file**: streamlit/app.py
- **Secrets**: configurados en Streamlit Cloud dashboard
- **Credenciales**: via `st.secrets` — nunca hardcodeadas en el repo

---

## 📅 Entrada #019 – Deploy final y cierre del proyecto

**Fecha:** 22/04/2026
**Autores:** Grupo 5

### Hito alcanzado
Sistema completo desplegado y funcional end-to-end.
Frontend accesible desde URL pública de Streamlit Cloud.

### Stack completo del proyecto

| Capa | Tecnología | Detalles |
|---|---|---|
| Dataset | HuggingFace McAuley-Lab | 190,750 reseñas · 3 categorías |
| ETL | AWS Glue v3 (Spark) | TSV → Neo4j AuraDB · 8 steps · MERGE idempotente |
| Graph DB | Neo4j AuraDB Free | 150,323 nodos · 344,749 relaciones |
| RAG Pipeline | AWS Lambda Python 3.11 | 6 intents · 6 queries Cypher |
| LLM | Amazon Bedrock Nova Micro | eu.amazon.nova-micro-v1:0 · eu-west-3 |
| API | AWS API Gateway REST | /prod/g5-lambda-sot |
| Secrets | AWS Secrets Manager | neo4j-g5-secret |
| Frontend | Streamlit Cloud | subgrafo pyvis interactivo |
| IaC | AWS CloudFormation | VPC, IAM, Lambda, API Gateway |
| Repositorio | GitHub | GabrielFFerspin/Proyecto-G5-SOT |

### Métricas finales del sistema

| Métrica | Valor |
|---|---|
| Reseñas procesadas | 190,750 |
| Productos únicos | 107,021 |
| Reviewers únicos | 43,299 |
| Categorías | 3 |
| Co-compras (CO_PURCHASED) | 19,167 |
| Nodos totales AuraDB | 150,323 |
| Relaciones totales AuraDB | 344,749 |
| Intents del RAG | 6 |
| Bots eliminados | 15 |
| Cobertura product_title | 94.8 % |

### Estado final
```
✅ Dataset multi-categoría       190,750 reseñas · 3 categorías
✅ Filtrado de bots              15 reviewers eliminados
✅ Bayesian score                C=10 · mean=4.32
✅ AWS Glue v3                   cargado en AuraDB · MERGE idempotente
✅ Neo4j AuraDB                  150,323 nodos · 344,749 relaciones
✅ Lambda RAG                    6 intents · respuestas en español
✅ API Gateway                   /prod/g5-lambda-sot · NONE auth
✅ Streamlit frontend            3 tabs · subgrafo pyvis interactivo
✅ Deploy Streamlit Cloud        URL pública · secrets seguros
✅ GitHub repo                   código completo documentado
```

---

*Fin del project log — Grupo 5 · Knowledge Assistant RAG · Abril 2026*

# Knowledge Assistant – RAG con Neo4j y Amazon Bedrock

## 📌 Descripción del proyecto
Este proyecto consiste en la construcción de un **asistente inteligente basado en Retrieval Augmented Generation (RAG)** que permite responder preguntas complejas sobre un catálogo de productos, clientes y compras utilizando:

- **Grafo de conocimiento en Neo4j**
- **LLM de Amazon Bedrock**
- **Arquitectura serverless y servicios AWS**

El objetivo es demostrar cómo combinar **datos estructurados + relaciones + LLMs** para obtener respuestas precisas, explicables y trazables.

---

## 👥 Equipo
Proyecto desarrollado por un equipo de **5 personas**.

| Nombre | Responsabilidades |
|------|-------------------|
| Julián Romero Parejo |  |
| Pablo Álvarez Arnedo |  |
| Alvaro Prieto Cano  |  |
| Lucia Huergo |  |
| Gabriel Fernandes Pinheiro |  |

---

## 🎯 Objetivos
- Construir una plataforma **RAG end-to-end** sobre AWS
- Modelar un **grafo de conocimiento** a partir de datos reales
- Responder preguntas de negocio complejas en lenguaje natural
- Desplegar toda la infraestructura como **Infrastructure as Code**

---

## 📂 Dataset
**Amazon Product Reviews (Electronics – subset)**  
- Fuente: Registry of Open Data on AWS  
- Registros utilizados: ~50.000  
- Campos principales:
  - `product_id`
  - `product_title`
  - `product_category`
  - `star_rating`
  - `review_headline`
  - `review_body`
  - `customer_id`
  - `purchase_date`

---

## 🧠 Modelado del grafo (Neo4j)

### Entidades
- `(:Product)`
- `(:Customer)`
- `(:Review)`

### Relaciones
- `(:Customer)-[:PURCHASED]->(:Product)`
- `(:Customer)-[:WROTE]->(:Review)`
- `(:Review)-[:ABOUT]->(:Product)`
- `(:Product)-[:SIMILAR_TO]->(:Product)` (co-compra)

### Decisiones de modelado
> Explicar aquí por qué se eligieron estas entidades y relaciones.

---

## 🏗️ Arquitectura

### Visión general
La arquitectura se divide en los siguientes bloques:

1. **Ingesta**
   - S3 (datos raw)
   - AWS Glue (ETL)
   - CloudFormation

2. **Persistencia**
   - EC2 + Neo4j
   - VPC privada + Security Groups
   - Roles IAM

3. **RAG & LLM**
   - AWS Lambda (orquestación RAG)
   - Amazon Bedrock (Claude / Titan)
   - API Gateway (REST)

4. **Observabilidad**
   - CloudWatch (logs y métricas)

---

## ⚙️ Infraestructura como Código (IaC)

### Servicios desplegados
- EC2 (Neo4j)
- VPC
- Subnets
- Security Groups
- IAM Roles
- API Gateway
- Lambda

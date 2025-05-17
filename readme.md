# CoinmarketCap Serverless Pipeline

A data engineer build a simple serverless pipeline with Azure services

## Graph Architecture Diagram

```mermaid
graph LR
    A[CoinMarketCap API] --> B(Azure Function);
    B -- Stores Raw Data (JSON) --> C[Azure Data Lake Storage Gen2 - Raw Zone];
    B -- Reads API Key --> D[Azure Key Vault];
    E(Databricks Job / Notebook) -- Reads Raw Data --> C;
    E -- Processes & Transforms --> F[Azure Data Lake Storage Gen2 - Processed Zone / Delta Lake];
    F -- Can be Queried By --> G{Azure Synapse Analytics};
    F -- Can be Queried By --> E;
    G -- Serves Data --> H[BI Tools / Applications / SQL Clients];
    E -- Serves Data --> H;
    I(Scheduler / Trigger) --> B;
    J(Scheduler / Trigger / ADF) --> E;




    subgraph Ingestion
        B
        D
    end

    subgraph Storage
        C
        F
    end

    subgraph Processing & Analytics
        E
        G
    end

    subgraph Serving
        H
    end

    subgraph Orchestration & Scheduling
        I
        J
    end


    style C fill:#f9f,stroke:#333,stroke-width:2px
    style F fill:#ccf,stroke:#333,stroke-width:2px
    style B fill:#bbf,stroke:#333,stroke-width:2px
    style E fill:#fbc,stroke:#333,stroke-width:2px
    style G fill:#cfc,stroke:#333,stroke-width:2px
``` 

## Architecture

![Architecture](serverless.drawio.png)


### Unnecessary services

Based on this project:

1. ADF
2. Azure Synapse Analytics

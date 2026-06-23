"""Render the ShopSage AWS architecture as a PNG with official AWS icons.

    pip install diagrams   (needs graphviz: brew install graphviz)
    python demo/architecture_diagram.py   ->   demo/shopsage-architecture.png
"""

from diagrams import Cluster, Diagram, Edge
from diagrams.aws.compute import Fargate, Lambda
from diagrams.aws.database import RDS
from diagrams.aws.integration import SQS
from diagrams.aws.ml import Bedrock
from diagrams.aws.network import CloudFront, ELB
from diagrams.aws.security import Cognito, SecretsManager
from diagrams.aws.storage import S3
from diagrams.onprem.client import User

graph_attr = {"fontsize": "20", "bgcolor": "white", "pad": "0.5"}

with Diagram(
    "ShopSage — AI Shopping Assistant on AWS",
    filename="demo/shopsage-architecture",
    outformat="png",
    show=False,
    direction="LR",
    graph_attr=graph_attr,
):
    shopper = User("Shopper")
    admin = User("Admin")
    bedrock = Bedrock("Bedrock\nClaude + Titan")

    with Cluster("Frontend"):
        cdn = CloudFront("CloudFront")
        static = S3("S3 (static site)")
        cdn >> static

    with Cluster("Backend"):
        alb = ELB("ALB")
        api = Fargate("ECS Fargate\nFlask agent + C retriever")
        alb >> api

    db = RDS("PostgreSQL\n+ pgvector")
    secrets = SecretsManager("Secrets\n(DATABASE_URL)")
    cognito = Cognito("Cognito")

    with Cluster("Event-driven ingestion"):
        docs = S3("S3 (docs)")
        queue = SQS("SQS + DLQ")
        worker = Lambda("Lambda\nchunk + embed")
        docs >> Edge(label="ObjectCreated") >> queue >> worker

    # request path
    shopper >> cdn
    shopper >> Edge(label="chat") >> alb
    shopper >> Edge(style="dashed") >> cognito
    api >> Edge(label="RAG + tools") >> db
    api >> Edge(label="generate") >> bedrock
    api >> secrets

    # ingestion path
    admin >> Edge(label="upload") >> docs
    worker >> Edge(label="embeddings") >> db
    worker >> Edge(label="Titan") >> bedrock

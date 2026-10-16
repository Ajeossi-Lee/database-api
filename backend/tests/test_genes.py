import pytest
from uuid import UUID
from httpx import AsyncClient
from app.main import app
from app.db.session import get_db
from app.modules.genes.models import Gene
from app.modules.genes.schemas import GeneCreate, GeneUpdate
from sqlalchemy.ext.asyncio import AsyncSession


CHROMOSOME_ID = "11111111-1111-1111-1111-111111111111"


@pytest.mark.asyncio
class TestGeneEndpoints:
    """Test gene endpoints."""

    @pytest.fixture
    async def client(self):
        """Create test client."""
        async with AsyncClient(app=app, base_url="http://test") as ac:
            yield ac

    @pytest.mark.asyncio
    async def test_create_gene(self, client: AsyncClient):
        """Test creating a gene."""
        gene_data = {
            "chromosome_id": CHROMOSOME_ID,
            "name": "TP53",
            "description": "Tumor protein p53"
        }

        response = await client.post("/api/v1/genes", json=gene_data)
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "TP53"
        assert data["data"]["description"] == "Tumor protein p53"
        assert "id" in data["data"]

    @pytest.mark.asyncio
    async def test_get_gene(self, client: AsyncClient):
        """Test getting a gene."""
        # First create a gene
        gene_data = {
            "chromosome_id": CHROMOSOME_ID,
            "name": "BRCA1",
            "description": "Breast cancer type 1 susceptibility protein"
        }

        create_response = await client.post("/api/v1/genes", json=gene_data)
        assert create_response.status_code == 200
        gene_id = create_response.json()["data"]["id"]

        # Then get the gene
        response = await client.get(f"/api/v1/genes/{gene_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["name"] == "BRCA1"
        assert data["data"]["description"] == "Breast cancer type 1 susceptibility protein"

    @pytest.mark.asyncio
    async def test_list_genes(self, client: AsyncClient):
        """Test listing genes."""
        # Create multiple genes
        gene_data = [
            {
                "chromosome_id": CHROMOSOME_ID,
                "name": "TP53",
                "description": "Tumor protein p53",
            },
            {
                "chromosome_id": CHROMOSOME_ID,
                "name": "BRCA1",
                "description": "Breast cancer type 1 susceptibility protein",
            },
        ]

        for data in gene_data:
            await client.post("/api/v1/genes", json=data)

        # List genes
        response = await client.get("/api/v1/genes")
        assert response.status_code == 200
        data = response.json()
        assert "data" in data
        assert "items" in data["data"]
        assert len(data["data"]["items"]) >= 2

    @pytest.mark.asyncio
    async def test_update_gene(self, client: AsyncClient):
        """Test updating a gene."""
        # Create a gene first
        gene_data = {
            "chromosome_id": CHROMOSOME_ID,
            "name": "MYC",
            "description": "MYC proto-oncogene"
        }

        create_response = await client.post("/api/v1/genes", json=gene_data)
        assert create_response.status_code == 200
        gene_id = create_response.json()["data"]["id"]

        # Update the gene
        update_data = {
            "name": "MYC",
            "description": "MYC proto-oncogene (updated)"
        }

        response = await client.put(f"/api/v1/genes/{gene_id}", json=update_data)
        assert response.status_code == 200
        data = response.json()
        assert data["data"]["description"] == "MYC proto-oncogene (updated)"

    @pytest.mark.asyncio
    async def test_delete_gene(self, client: AsyncClient):
        """Test deleting a gene."""
        # Create a gene first
        gene_data = {
            "chromosome_id": CHROMOSOME_ID,
            "name": "EGFR",
            "description": "Epidermal growth factor receptor"
        }

        create_response = await client.post("/api/v1/genes", json=gene_data)
        assert create_response.status_code == 200
        gene_id = create_response.json()["data"]["id"]

        # Delete the gene
        response = await client.delete(f"/api/v1/genes/{gene_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Gene deleted successfully"
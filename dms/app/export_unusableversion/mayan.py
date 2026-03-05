import requests
from app.db import get_conn
from app.export.field_mapping import FIELD_MAPPING


class MayanClient:
    """Define the mayan client type.
    
    Parameters:
        None.
    """
    def __init__(self, base_url, api_token):
        """Initialize the instance state.

        Parameters:
            base_url: Function argument used by this operation.
            api_token: Function argument used by this operation.
        """
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Token {api_token}",
            "Content-Type": "application/json",
        })

    def set_metadata(self, mayan_doc_id, metadata_type_id, value):
        """Set metadata.

        Parameters:
            mayan_doc_id: Identifier used to locate the target record.
            metadata_type_id: Identifier used to locate the target record.
            value: Function argument used by this operation.
        """
        url = f"{self.base_url}/api/v4/documents/{mayan_doc_id}/metadata/"
        payload = {
            "metadata_type_id": metadata_type_id,
            "value": value,
        }
        self.session.post(url, json=payload)


def export_document_to_mayan(document_id: str, mayan_doc_id: int, client: MayanClient):
    """Handle export document to mayan.

    Parameters:
        document_id (type=str): Identifier used to locate the target record.
        mayan_doc_id (type=int): Identifier used to locate the target record.
        client (type=MayanClient): Function argument used by this operation.
    """
    conn = get_conn()

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT doc_class
            FROM documents
            WHERE id = %s
            """,
            (document_id,),
        )
        doc_class = cur.fetchone()[0]

        cur.execute(
            """
            SELECT field_name, field_value
            FROM document_fields
            WHERE document_id = %s
            """,
            (document_id,),
        )
        fields = cur.fetchall()

    mapping = FIELD_MAPPING.get(doc_class, {})

    for field_name, field_value in fields:
        if field_name not in mapping:
            continue

        metadata_label = mapping[field_name]

        # You must pre-create metadata types in Mayan
        metadata_type_id = lookup_mayan_metadata_type_id(metadata_label)

        client.set_metadata(mayan_doc_id, metadata_type_id, field_value)


def lookup_mayan_metadata_type_id(label: str) -> int:
    """Placeholder: resolve label → metadata_type_id.

    Parameters:
        label (type=str): Function argument used by this operation.
    """
    raise NotImplementedError("Map metadata labels to Mayan metadata_type_id")

from graph import extended_metadata, primary_email
from jobs import role_key_for_group, role_display_for_group


def test_primary_email_prefers_mail():
    assert primary_email({"mail": "A@B.com", "userPrincipalName": "x@y.com"}) == "a@b.com"


def test_primary_email_falls_back_to_upn():
    assert primary_email({"mail": None, "userPrincipalName": "X@Y.com"}) == "x@y.com"


def test_primary_email_none_when_absent():
    assert primary_email({}) is None


def test_extended_metadata_maps_fields():
    user = {
        "id": "oid-123",
        "jobTitle": "Engineer",
        "department": "IT",
        "companyName": "BAUER GROUP",
        "mobilePhone": "+49 170 0000000",
        "businessPhones": ["+49 7551 111", "+49 7551 222"],
        "faxNumber": "+49 7551 999",
        "officeLocation": "HQ",
    }
    md = extended_metadata(user)
    assert md["entra_oid"] == "oid-123"
    assert md["job_title"] == "Engineer"
    assert md["office_phone"] == "+49 7551 111"  # first business phone
    assert md["fax_number"] == "+49 7551 999"


def test_extended_metadata_handles_missing():
    md = extended_metadata({"id": "x"})
    assert md["office_phone"] == ""
    assert md["department"] == ""


def test_role_key_is_namespaced_and_safe():
    g = {"id": "11111111-2222-3333-4444-555555555555", "displayName": "All Staff"}
    key = role_key_for_group("entra:", g)
    assert key.startswith("entra:")
    assert " " not in key
    # display keeps the human name
    assert role_display_for_group("entra:", g) == "entra:All Staff"

import asyncio
import ib_insync
from lxml import etree

def validate_xml(xml_string: str, xsd_path: str) -> None:
    # Parse XSD schema
    with open(xsd_path, "rb") as f:
        schema_doc = etree.parse(f)
    schema = etree.XMLSchema(schema_doc)

    # Parse XML document
    xml_doc = etree.fromstring(xml_string.encode("utf-8"))

    # Validate and raise with details on failure
    if not schema.validate(xml_doc):
        # Collect error messages
        log = schema.error_log
        msgs = [f"Line {e.line}, column {e.column}: {e.message}" for e in log]
        raise ValueError("XML failed validation:\n" + "\n".join(msgs))

async def main():
    ib = ib_insync.IB()
    await ib.connectAsync("127.0.0.1", 7496, clientId=1234)
    accounts = ib.managedAccounts()
    print(accounts)

    print(ib.portfolio())

    xml_str = await ib.requestFAAsync(1)
    assert xml_str
    validate_xml(xml_str, "faGroups.xsd")
    print(xml_str)


    await asyncio.sleep(10)
    return

if __name__ == "__main__":
    try:
        # asyncio.run(main())
        ib_insync.IB.run(main())
    except KeyboardInterrupt:
        print("Program interrupted by user")
    except Exception as e:
        print(f"An error occurred: {e}")
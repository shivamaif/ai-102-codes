from dotenv import load_dotenv
import os

from azure.core.credentials import AzureKeyCredential
from azure.ai.formrecognizer import DocumentAnalysisClient


def main():

    # Clear the console
    os.system('cls' if os.name == 'nt' else 'clear')

    try:
        # Get config settings
        load_dotenv()
        endpoint = os.getenv('ENDPOINT')
        key = os.getenv('KEY')

        # Set analysis settings
        fileUri = "https://github.com/MicrosoftLearning/mslearn-ai-information-extraction/blob/main/Labfiles/prebuilt-doc-intelligence/sample-invoice/sample-invoice.pdf?raw=true"
        fileLocale = "en-US"
        fileModelId = "prebuilt-invoice"

        print(f"\nConnecting to Forms Recognizer at: {endpoint}")
        print(f"Analyzing invoice at: {fileUri}")

        # Create the client
        document_analysis_client = DocumentAnalysisClient(
            endpoint=endpoint,
            credential=AzureKeyCredential(key)
        )

        # Analyse the invoice
        poller = document_analysis_client.begin_analyze_document_from_url(
            fileModelId,
            fileUri,
            locale=fileLocale
        )

        # Display invoice information to the user
        receipts = poller.result()

        for idx, receipt in enumerate(receipts.documents):

            vendor_name = receipt.fields.get("VendorName")
            if vendor_name:
                print(
                    f"\nVendor Name: {vendor_name.value}, "
                    f"with confidence {vendor_name.confidence}."
                )

            customer_name = receipt.fields.get("CustomerName")
            if customer_name:
                print(
                    f"Customer Name: {customer_name.value}, "
                    f"with confidence {customer_name.confidence}."
                )

            invoice_total = receipt.fields.get("InvoiceTotal")
            if invoice_total:
                print(
                    f"Invoice Total: {invoice_total.value.symbol}"
                    f"{invoice_total.value.amount}, "
                    f"with confidence {invoice_total.confidence}."
                )

    except Exception as ex:
        print(ex)

    print("\nAnalysis complete.\n")


if __name__ == "__main__":
    main()

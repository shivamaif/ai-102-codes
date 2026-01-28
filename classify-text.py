from dotenv import load_dotenv
import os

from azure.core.credentials import AzureKeyCredential
from azure.ai.textanalytics import TextAnalyticsClient


def main():
    try:
        # Load environment variables
        load_dotenv()
        ai_endpoint = os.getenv('AI_SERVICE_ENDPOINT')
        ai_key = os.getenv('AI_SERVICE_KEY')
        project_name = os.getenv('PROJECT')
        deployment_name = os.getenv('DEPLOYMENT')

        # Create client
        credential = AzureKeyCredential(ai_key)
        ai_client = TextAnalyticsClient(
            endpoint=ai_endpoint,
            credential=credential
        )

        # Read each text file in the articles folder
        batched_documents = []
        articles_folder = 'articles'
        files = os.listdir(articles_folder)

        for file_name in files:
            file_path = os.path.join(articles_folder, file_name)
            with open(file_path, encoding='utf-8') as f:
                batched_documents.append(f.read())

        # Get classifications
        operation = ai_client.begin_single_label_classify(
            batched_documents,
            project_name=project_name,
            deployment_name=deployment_name
        )

        document_results = operation.result()

        for doc, classification_result in zip(files, document_results):
            if classification_result.kind == "CustomDocumentClassification":
                classification = classification_result.classifications[0]
                print(
                    f"{doc} was classified as "
                    f"'{classification.category}' "
                    f"with confidence score {classification.confidence_score}."
                )
            elif classification_result.is_error:
                print(
                    f"{doc} has an error with code "
                    f"'{classification_result.error.code}' "
                    f"and message '{classification_result.error.message}'."
                )

    except Exception as ex:
        print(ex)


if __name__ == "__main__":
    main()

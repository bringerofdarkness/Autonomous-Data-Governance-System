import asyncio
from app.services.llm_service import LLMGenerationService

async def run_isolated_audit():
    print("[*] Initializing LLM Generation Engine...")
    service = LLMGenerationService()
    print(f"[+] Active Provider: {service.provider}")
    
    mock_chunks = [
        {
            "text": "Enterprise Policy ADGS-2026 mandates that all financial transaction logs must be retained for exactly 7 years.",
            "point_id": "8e3eb05d-2812-4f2e-a9ec-ce734f2ea9ec",
            "metadata": {"document_id": "policy-fin-001"}
        },
        {
            "text": "Financial records retention over 5 years requires implicit approval from the Chief Compliance Officer.",
            "point_id": "5a4cb756-b40d-4194-a9ec-4f2ea9ecce73",
            "metadata": {"document_id": "policy-fin-001"}
        }
    ]
    
    test_question = "What is the retention period for financial transaction logs according to the audit records?"
    
    print(f"[*] Dispatching Test Query: '{test_question}'")
    try:
        result = service.synthesize_answer(test_question, mock_chunks)
        print("\n=== SYSTEM SYNTHESIS RESPONSE ===")
        print(f"Answer: {result.get('answer')}")
        print(f"Provider Emitted: {result.get('provider')}")
        print(f"Citations Extracted Count: {len(result.get('citations', []))}")
        print("=================================\n")
    except Exception as e:
        print(f"[-] Pipeline Test Exception Captured: {str(e)}")

if __name__ == "__main__":
    asyncio.run(run_isolated_audit())
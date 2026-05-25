import httpx
import asyncio

async def main():
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get('http://localhost:8000/subjects')
            print("Status:", r.status_code)
            print("Subjects:", r.json())
        except Exception as e:
            print("Error:", e)

if __name__ == "__main__":
    asyncio.run(main())

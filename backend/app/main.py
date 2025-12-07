from fastapi import FastAPI

app = FastAPI(
    title="Next-Gen Backend API",
    description="A Fully-featured backend API for modern applications.",
)


@app.get("/")
async def root():
    return {"message": "Welcome to the Next-Gen Backend API!"}
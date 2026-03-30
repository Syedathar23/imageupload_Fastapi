import tempfile
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException,File,UploadFile,Form,Depends
from pyexpat.errors import messages
from sqlalchemy.orm import selectinload

from app.schemas import Postcreate, UserRead, UserCreate, UserUpdate
from app.db import Post,create_db_and_tables, get_async_session,User
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
from sqlalchemy import select
from app.images import imagekit
# from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions
import os
import shutil
import uuid
from app.users import auth_backend,current_active_user,fastapi_users


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(fastapi_users.get_auth_router(auth_backend), prefix="/auth/jwt", tags=["auth"])
app.include_router(fastapi_users.get_register_router(UserRead, UserCreate), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_reset_password_router(), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_verify_router(UserRead), prefix="/auth", tags=["auth"])
app.include_router(fastapi_users.get_users_router(UserRead, UserUpdate), prefix="/users", tags=["users"])
@app.post("/upload")
async def upload_file(
        file:UploadFile=File(...),
        caption: str = Form(""),
        user : User=Depends(current_active_user),
        session: AsyncSession= Depends(get_async_session)
):
    temp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as temp_file:
            temp_file_path = temp_file.name
            shutil.copyfileobj(file.file, temp_file)

        upload_result = imagekit.upload_file(
            file=open(temp_file_path, "rb"),
            file_name=file.filename,
            options={
                "folder": "/uploads/",
                "tags": ["backend-upload"]
            }
        )

        if upload_result.response_metadata.http_status_code == 200:
            post = Post(
                caption=caption,
                url=upload_result.url,
                file_type="video" if file.content_type.startswith("video/") else "image",
                file_name=upload_result.name,
            )
            session.add(post)
            await session.commit()
            await session.refresh(post)
            return post
    except Exception as e:
        return {"error": str(e)}
    finally:
        if temp_file_path and os.path.exists(temp_file_path):
            os.unlink(temp_file_path)
        file.file.close()

@app.get("/feed")
async def get_data(
        session:AsyncSession=Depends(get_async_session),
        user: User = Depends(current_active_user),

):
    result = await session.execute(select(Post).options(selectinload(Post.user)).order_by(Post.created_at.desc()))
    posts = [row[0] for row in result.all()]

    result=await session.execute(select(User))
    users=[row[0] for row in result.all()]
    user_dict = {u.id:u.email for u in users}

    posts_data = []
    for post in posts:
        posts_data.append({
            "id": str(post.id),
            "User_id": str(post.user_id),
            "caption": post.caption,
            "url": post.url,
            "file_name": post.file_name,
            "file_type": post.file_type,
            "created_at": post.created_at.isoformat(),
            "is_owner": post.user_id == user.id,
            "email": user_dict.get(post.user_id),
        })
    return {"posts": posts_data}


@app.delete("/posts/{post_id}")
async def delete_post(post_id:str,session:AsyncSession=Depends(get_async_session), user:User=Depends(current_active_user)):
    try:
        post_uuid=uuid.UUID(post_id)
        result = await session.execute(select(Post).where(Post.id==post_id))
        post = result.scalars().first()
        print(f"Found: {result}")

        if not post:
            raise HTTPException(status_code=404, detail="Post not found")

        if post.user_id != user.id:
            raise HTTPException(status_code=403, detail="You do not have permission to perform this action")
        await session.delete(post)
        await session.commit()

        return {"success":True,"message":"Post is deleted sucessfully"}
    except HTTPException:
        raise
    except Exception as e:
        return {"error": str(e)}

























#
# text_posts = {
#     1: {"title": "name1", "role": "user"},
#     2: {"title": "name2", "role": "user"},
#     3: {"title": "name3", "role": "user"}
# }
# @app.get("/posts")
# def posts(limit: int = None):
#     if limit>:
#         return dict(list(text_posts.items())[:limit])
#     return text_posts
#
#
# @app.get("/posts/{id}")
# def get_post(id: int):
#     if id not in text_posts:
#         raise HTTPException(status_code=404,detail="post not found")
#
#     return text_posts[id]
#
#
# @app.post("/post")
# def create_post(post: Postcreate):
#     newobject ={"title":post.title , "content" : post.content}
#     text_posts[max(text_posts.keys())+1] = newobject
#     return text_posts

from tortoise import fields
from tortoise.models import Model
from tortoise.contrib.pydantic import pydantic_model_creator
from enum import Enum

class PostType(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    VIDEO = "video"
    LINK = "link"

class Profile(Model):
    id = fields.IntField(pk=True)
    user = fields.OneToOneField('models.User', related_name='profile')
    bio = fields.TextField(null=True)
    avatar = fields.CharField(max_length=255, null=True)
    cover_image = fields.CharField(max_length=255, null=True)
    location = fields.CharField(max_length=100, null=True)
    website = fields.CharField(max_length=255, null=True)
    followers_count = fields.IntField(default=0)
    following_count = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "profiles"
        indexes = [("user_id",)]

class Post(Model):
    id = fields.BigIntField(pk=True)
    author = fields.ForeignKeyField('models.User', related_name='posts')
    content = fields.TextField()
    post_type = fields.CharEnumField(PostType)
    media_url = fields.CharField(max_length=255, null=True)
    likes_count = fields.IntField(default=0)
    comments_count = fields.IntField(default=0)
    shares_count = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "posts"
        indexes = [("author_id",), ("created_at",)]

class Comment(Model):
    id = fields.BigIntField(pk=True)
    post = fields.ForeignKeyField('models.Post', related_name='comments')
    author = fields.ForeignKeyField('models.User', related_name='comments')
    content = fields.TextField()
    likes_count = fields.IntField(default=0)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "comments"
        indexes = [("post_id",), ("author_id",)]

class ChatRoom(Model):
    id = fields.BigIntField(pk=True)
    name = fields.CharField(max_length=255, null=True)
    is_group = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)

    class Meta:
        table = "chat_rooms"
        indexes = [("created_at",)]

class ChatParticipant(Model):
    id = fields.BigIntField(pk=True)
    room = fields.ForeignKeyField('models.ChatRoom', related_name='participants')
    user = fields.ForeignKeyField('models.User', related_name='chat_participants')
    joined_at = fields.DatetimeField(auto_now_add=True)
    last_read_at = fields.DatetimeField(null=True)

    class Meta:
        table = "chat_participants"
        indexes = [("room_id", "user_id")]

class ChatMessage(Model):
    id = fields.BigIntField(pk=True)
    room = fields.ForeignKeyField('models.ChatRoom', related_name='messages')
    sender = fields.ForeignKeyField('models.User', related_name='sent_messages')
    content = fields.TextField()
    is_read = fields.BooleanField(default=False)
    created_at = fields.DatetimeField(auto_now_add=True)

    class Meta:
        table = "chat_messages"
        indexes = [("room_id", "created_at"), ("sender_id",)]

# Pydantic models
Profile_Pydantic = pydantic_model_creator(Profile, name="Profile")
ProfileIn_Pydantic = pydantic_model_creator(
    Profile,
    name="ProfileIn",
    exclude_readonly=True
)

Post_Pydantic = pydantic_model_creator(Post, name="Post")
PostIn_Pydantic = pydantic_model_creator(
    Post,
    name="PostIn",
    exclude_readonly=True
)

Comment_Pydantic = pydantic_model_creator(Comment, name="Comment")
CommentIn_Pydantic = pydantic_model_creator(
    Comment,
    name="CommentIn",
    exclude_readonly=True
)

ChatRoom_Pydantic = pydantic_model_creator(ChatRoom, name="ChatRoom")
ChatRoomIn_Pydantic = pydantic_model_creator(
    ChatRoom,
    name="ChatRoomIn",
    exclude_readonly=True
)

ChatMessage_Pydantic = pydantic_model_creator(ChatMessage, name="ChatMessage")
ChatMessageIn_Pydantic = pydantic_model_creator(
    ChatMessage,
    name="ChatMessageIn",
    exclude_readonly=True
) 
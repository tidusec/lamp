from fastapi import FastAPI, Request, Depends
from starlette.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import Annotated
from fastapi import Body, Cookie, File, Form, Header, Path, Query
from pydantic import BaseModel
from sqlmodel import Field, Session, SQLModel, create_engine, select
from datetime import datetime
import pandas as pd
app = FastAPI()

connection_url = f"mysql+pymysql://root:root@mariadb/lamp?charset=utf8mb4"


connect_args = {"check_same_thread": False}
engine = create_engine(connection_url, connect_args=connect_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

# Code above omitted 👆

def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]

# Code below omitted 👇

@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    con = engine.connect()
    pd.read_sql("CREATE USER IF NOT EXISTS 'nonprivileged' IDENTIFIED BY 'nonprivileged';", con)
    pd.read_sql("GRANT INSERT, UPDATE, SELECT ON lamp.ships TO 'nonprivileged';", con)
    pd.read_sql("GRANT INSERT, UPDATE, SELECT ON lamp.components TO 'nonprivileged';", con)
    pd.read_sql("GRANT INSERT, SELECT ON lamp.connections TO 'nonprivileged';")
    pd.read_sql("FLUSH PRIVILEGES;")


class Ships(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    username: str = Field(index=True, unique=True)
    numComponents: int = Field(default=0)
    created: datetime = Field(default=datetime.now())


class Components(SQLModel, table=True):
    id: int = Field(default=None, primary_key=True)
    type: str|None = Field(index=True)
    x: float|None = Field(index=True)
    y: float|None = Field(index=True)
    state: int|None = Field()
    properties: str = Field(default='1')
    ship: int = Field(foreign_key="ships.id", ondelete="CASCADE")

class Connections(SQLModel, table=True):
    src: int = Field(default=None, primary_key=True)
    dst: int = Field(default=None, index=True, primary_key=True)

class User(SQLModel, table=True):
    username: str = Field(default="", primary_key=True)
    password: str = Field(default="")
    session_id: str = Field(default="")
    shipname: str = Field(default="")




app.mount("/www", StaticFiles(directory="www"), name="static")


templates = Jinja2Templates(directory="templates")
@app.get("/")
async def root(request: Request):
    #ifLoggedIn():
        # addSubmitForm
        # title = 'Ship "' + shipName + '"'
    # else:
    #     title = " LAMP"

    title = "LAMP"
    overviewButton = """
    <a class="menu-item highlight" href="/">Overview</a>
    """
    loginButton = """
    <a class="menu-item" href="/login">Login</a>
    """
    registerButton = """
    <a class="menu-item" href="/register">Register</a>
    """
    overviewButtons = overviewButton
    buttons = loginButton + registerButton

    #ifLoggedIn():
    # buttons = """
    # <a class="menu-item" href="/logout">Logout</a>
    # """


    return templates.TemplateResponse(
        request=request, name="lamp.html", context={"title": title, "buttons": buttons, "overviewButtons": overviewButtons}
    )


@app.get("/register")
async def registerGet(request: Request):
    title = "LAMP"
    overviewButton = """
                <a class="menu-item" href="/">Overview</a>
                """
    loginButton = """
                <a class="menu-item" href="/login">Login</a>
                """
    registerButton = """
                <a class="menu-item highlight" href="/register">Register</a>
                """
    overviewButtons = overviewButton
    buttons = loginButton + registerButton

    content = """
        <div id="content">
        <h1> Register</h1>
        <form method="POST"><label>Username:</label><input type="text" name="username" /><label>Password:</label><input type="text" name="password" /><label>Name of ship:</label><input type="text" name="shipname" /><input type="submit" value="Register" /></form>
    </div>
        """

    # ifLoggedIn():
    # redirect("/")

    return templates.TemplateResponse(
        request=request, name="lamp.html",
        context={"title": title, "buttons": buttons, "overviewButtons": overviewButtons, "content": content}
    )


@app.get("/login")
async def loginGet(request: Request):
    title = "LAMP"
    overviewButton = """
            <a class="menu-item" href="/">Overview</a>
            """
    loginButton = """
            <a class="menu-item highlight" href="/login">Login</a>
            """
    registerButton = """
            <a class="menu-item" href="/register">Register</a>
            """
    overviewButtons = overviewButton
    buttons = loginButton + registerButton

    content = """
    <div id="content">
        <h1> Login</h1>
        <form method="POST"><label>Username:</label><input type="text" name="username" /><label>Password:</label><input type="text" name="password" /><input type="submit" value="Log In" /></form>
    </div>
    """

    # ifLoggedIn():
    # redirect("/")

    return templates.TemplateResponse(
        request=request, name="lamp.html",
        context={"title": title, "buttons": buttons, "overviewButtons": overviewButtons, "content": content}
    )

class Login(BaseModel):
    username: str = ""
    password: str = ""

@app.post("/login")
async def loginPost(request: Request, data: Annotated[Login, Form()], session: SessionDep):


    title = "LAMP"

    overviewButton = """
                <a class="menu-item" href="/">Overview</a>
                """
    loginButton = """
                <a class="menu-item highlight" href="/login">Login</a>
                """
    registerButton = """
                <a class="menu-item" href="/register">Register</a>
                """
    overviewButtons = overviewButton
    buttons = loginButton + registerButton

    user = session.get(User, data.username)
    logged_in = True

    if not user or user.password != data.password:
        logged_in = False

    # if success
    content = """
        <div id="content">
        <h1> Login</h1>
        <p>Successfully logged in</p>
        <meta http-equiv="Refresh" content="2;url=/" />
    </div>
        """


    # if fail
    if not logged_in:
        content = """<div id="content">
                <h1> Login</h1>
                <p>Failed to log in</p>
                <form method="POST"><label>Username:</label><input type="text" name="username" /><label>Password:</label><input type="text" name="password" /><input type="submit" value="Log In" /></form>
            </div>
            """

    # ifLoggedIn():
    # redirect("/")

    return templates.TemplateResponse(
        request=request, name="lamp.html",
        context={"title": title, "buttons": buttons, "overviewButtons": overviewButtons, "content": content}
    )


@app.post("/register")
async def registerPost(request: Request):
    title = "LAMP"
    overviewButton = """
                <a class="menu-item" href="/">Overview</a>
                """
    loginButton = """
                <a class="menu-item highlight" href="/login">Login</a>
                """
    registerButton = """
                <a class="menu-item" href="/register">Register</a>
                """
    overviewButtons = overviewButton
    buttons = loginButton + registerButton

    # if success
    content = """
    <div id="content">
        <h1> Register</h1>
        <p>Successfully registered account</p>
        <meta http-equiv="Refresh" content="2;url=/" />
        </div>
        """

    # if fail
    content = """<div id="content">
        <h1> Register</h1>
        <p>Account already exists</p>
        <form method="POST"><label>Username:</label><input type="text" name="username" /><label>Password:</label><input type="text" name="password" /><label>Name of ship:</label><input type="text" name="shipname" /><input type="submit" value="Register" /></form>
    </div>
    """

    # ifLoggedIn():
    # redirect("/")

    return templates.TemplateResponse(
        request=request, name="lamp.html",
        context={"title": title, "buttons": buttons, "overviewButtons": overviewButtons, "content": content}
    )

print("Running server")
from fastapi import FastAPI, Request, Depends, Response
from starlette.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import Annotated
from fastapi import Body, Cookie, File, Form, Header, Path, Query
from pydantic import BaseModel
from sqlmodel import Field, Session, SQLModel, create_engine, select
from datetime import datetime
import pandas as pd
import time
from sqlalchemy import text
import random
import string

time.sleep(4)
app = FastAPI()

connection_url = f"mysql+pymysql://root:root@mariadb/lamp?charset=utf8mb4"


engine = create_engine(connection_url)

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
    con.execute(text("CREATE USER IF NOT EXISTS 'nonprivileged' IDENTIFIED BY 'nonprivileged';"))
    con.execute(text("GRANT INSERT, UPDATE, SELECT ON lamp.ships TO 'nonprivileged';"))
    con.execute(text("GRANT INSERT, UPDATE, SELECT ON lamp.components TO 'nonprivileged';"))
    con.execute(text("GRANT INSERT, SELECT ON lamp.connections TO 'nonprivileged';"))
    con.execute(text("FLUSH PRIVILEGES;"))
    con.close()


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




app.mount("/www", StaticFiles(directory="/www"), name="static")


templates = Jinja2Templates(directory="/templates")
@app.get("/")
async def root(request: Request, session: SessionDep):
    #ifLoggedIn():
        # addSubmitForm
        # title = 'Ship "' + shipName + '"'
    # else:
    #     title = " LAMP"
    authenticated = request.cookies.get("Session")


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

    content = """
            <div id="content">
        <h1> LAMP</h1>
        <p> <a href="/login">Log in</a> or <a href="/register">register</a> </p>
    </div>
            """

    if authenticated:
        user = session.query(User).filter_by(session_id=authenticated)
        first: User = user.first()
        if first:
            buttons = """
                <a class="menu-item" href="/logout">Logout</a>
            """

            content = """
            <div id="content">
                <h1> Ship "pvq"
                    <form method="POST" style="display: contents"><input type="hidden" name="action" value="tick" /><input type="submit" value="&#8635; Refresh" style="width: max-content; padding: 0 0.5rem; margin: 0" /></form>
                </h1>
                <div id="ship-wrapper">
                    <div id="components"> <input id="component-light" type="radio" name="component" value="light" checked /> <label for="component-light">Light</label> <input id="component-button" type="radio" name="component" value="button"> <label for="component-button">Button</label> <input id="component-source" type="radio" name="component" value="source"> <label for="component-source">Source</label> <br /> <label><input type="checkbox" id="connect-mode" /> Connect mode</label> </div>
                    <div id="canvas" data-tooltip="Click to add"> </div>
                </div>
            </div>
            
            """







    return templates.TemplateResponse(
        request=request, name="lamp.html", context={"title": title, "buttons": buttons, "overviewButtons": overviewButtons, "content": content}
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

    response =  templates.TemplateResponse(
        request=request, name="lamp.html",
        context={"title": title, "buttons": buttons, "overviewButtons": overviewButtons, "content": content}
    )

    return response


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

    response =  templates.TemplateResponse(
        request=request, name="lamp.html",
        context={"title": title, "buttons": buttons, "overviewButtons": overviewButtons, "content": content}
    )
    response.set_cookie(key="Session", value=user.session_id)
    return response


class Register(BaseModel):
    username: str = ""
    password: str = ""
    shipname: str = ""
@app.post("/register")
async def registerPost(request: Request, data: Annotated[Register, Form()], session: SessionDep):
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

    alreadyRegisteredUser = session.get(User, data.username)
    success = True
    if alreadyRegisteredUser:
        success = False

    length = 8
    random_string = ''.join(random.choices(string.ascii_letters + string.digits, k=length))

    registeredUser: User = User(
        username=data.username,
        password=data.password,
        shipname=data.shipname,
        session_id=random_string,
    )

    session.add(registeredUser)
    session.commit()
    session.refresh(User)

    # if success
    content = """
    <div id="content">
        <h1> Register</h1>
        <p>Successfully registered account</p>
        <meta http-equiv="Refresh" content="2;url=/" />
        </div>
        """

    if not success:
        content = """<div id="content">
            <h1> Register</h1>
            <p>Account already exists</p>
            <form method="POST"><label>Username:</label><input type="text" name="username" /><label>Password:</label><input type="text" name="password" /><label>Name of ship:</label><input type="text" name="shipname" /><input type="submit" value="Register" /></form>
        </div>
        """

    # ifLoggedIn():
    # redirect("/")

    response =  templates.TemplateResponse(
        request=request, name="lamp.html",
        context={"title": title, "buttons": buttons, "overviewButtons": overviewButtons, "content": content}
    )
    response.set_cookie(key="Session", value=registeredUser.session_id)
    return response

print("Running server")
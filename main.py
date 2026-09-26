from fastapi import FastAPI, Request, Depends
from starlette.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from typing import Annotated
from fastapi import Form
from pydantic import BaseModel
from sqlmodel import Field, Session, SQLModel, create_engine, select
from sqlalchemy import text
from sqlalchemy.orm import aliased
from starlette.status import HTTP_302_FOUND
import html
import time
import random
import string

time.sleep(4)
app = FastAPI()

connection_url = "mysql+pymysql://root:root@mariadb/lamp?charset=utf8mb4"
engine = create_engine(connection_url)

MAX_COMPONENTS = 50
COMPONENT_TYPES = {"light", "button", "source"}


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


SessionDep = Annotated[Session, Depends(get_session)]


@app.on_event("startup")
def on_startup():
    create_db_and_tables()
    with engine.connect() as con:
        con.execute(text("CREATE USER IF NOT EXISTS 'nonprivileged' IDENTIFIED BY 'nonprivileged';"))
        con.execute(text("GRANT INSERT, UPDATE, SELECT ON lamp.components TO 'nonprivileged';"))
        con.execute(text("GRANT INSERT, SELECT ON lamp.connections TO 'nonprivileged';"))
        con.execute(text("FLUSH PRIVILEGES;"))
        con.commit()


class User(SQLModel, table=True):
    username: str = Field(default="", primary_key=True)
    password: str = Field(default="")
    session_id: str = Field(default="")
    shipname: str = Field(default="")


class Components(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    type: str | None = Field(default=None, index=True)
    x: float | None = Field(default=None, index=True)
    y: float | None = Field(default=None, index=True)
    state: int | None = Field(default=0)
    properties: str = Field(default="off")  # buttons: "on" / "off"
    ship: str = Field()


class Connections(SQLModel, table=True):
    src: int = Field(primary_key=True)
    dst: int = Field(primary_key=True, index=True)


app.mount("/www", StaticFiles(directory="/www"), name="static")
templates = Jinja2Templates(directory="/templates")


# ---------------------------------------------------------------- helpers

def get_logged_in_user(request: Request, session: Session) -> User | None:
    session_id = request.cookies.get("Session")
    if not session_id:
        return None
    return session.exec(select(User).where(User.session_id == session_id)).first()


def tick(session: Session, shipname: str):
    """One simulation step: lights follow their inputs, buttons pass
    their input through only when switched on. Sources never change."""
    session.execute(
        text(
            "UPDATE components c "
            "LEFT JOIN (SELECT w.dst AS id, MAX(s.state) AS anyOn "
            "           FROM connections w JOIN components s ON s.id = w.src "
            "           WHERE s.ship = :ship GROUP BY w.dst) agg ON agg.id = c.id "
            "SET c.state = CASE c.type "
            "  WHEN 'light'  THEN COALESCE(agg.anyOn, 0) "
            "  WHEN 'button' THEN IF(c.properties = 'on' AND COALESCE(agg.anyOn, 0) = 1, 1, 0) "
            "  ELSE c.state END "
            "WHERE c.ship = :ship AND c.type <> 'source'"
        ),
        {"ship": shipname},
    )
    session.commit()


def render_canvas(session: Session, shipname: str) -> str:
    parts = []

    # Wires between components of this ship
    c1 = aliased(Components)
    c2 = aliased(Components)
    lines = session.exec(
        select(c1.x, c1.y, c2.x, c2.y, c1.state)
        .select_from(Connections)
        .join(c1, Connections.src == c1.id)
        .join(c2, Connections.dst == c2.id)
        .where(c1.ship == shipname, c2.ship == shipname)
    ).all()
    for x1, y1, x2, y2, state in lines:
        st = "on" if state == 1 else "off"
        parts.append(
            f'<div class="line {st}" data-x1="{x1}" data-y1="{y1}" '
            f'data-x2="{x2}" data-y2="{y2}"></div>'
        )

    # Components
    components = session.exec(select(Components).where(Components.ship == shipname)).all()
    for c in components:
        st = "on" if c.state == 1 else "off"
        ctype = html.escape(c.type or "")
        props = html.escape(c.properties or "")
        if c.type == "button":
            parts.append(
                '<form method="POST" style="display: contents">'
                f'<span class="component-wrap" data-id="{c.id}" style="position: absolute; left: {c.x}px; top: {c.y}px;">'
                f'<input class="component {ctype} {st}" data-properties="{props}" type="submit" '
                f"style=\"--img: url('/components/{ctype}_{st}.svg');margin: 0; padding: 0;\" value=\"\" />"
                "</span>"
                '<input type="hidden" name="action" value="toggle" />'
                f'<input type="hidden" name="id" value="{c.id}" />'
                "</form>"
            )
        else:
            parts.append(
                f'<span class="component-wrap" data-id="{c.id}" style="position: absolute; left: {c.x}px; top: {c.y}px;">'
                f'<input class="component {ctype} {st}" data-properties="{props}" type="submit" '
                f"style=\"--img: url('/components/{ctype}_{st}.svg');cursor: default; margin: 0; padding: 0;\" value=\"\" />"
                "</span>"
            )

    return "\n".join(parts)


# ---------------------------------------------------------------- main page

@app.get("/")
async def root(request: Request, session: SessionDep):
    title = "LAMP"
    overviewButtons = '<a class="menu-item highlight" href="/">Overview</a>'
    buttons = (
        '<a class="menu-item" href="/login">Login</a>'
        '<a class="menu-item" href="/register">Register</a>'
    )
    content = """
    <div id="content">
        <h1> LAMP</h1>
        <p> <a href="/login">Log in</a> or <a href="/register">register</a> to manage your ship</p>
    </div>
    """

    user = get_logged_in_user(request, session)
    if user:
        buttons = '<a class="menu-item" href="/logout">Logout</a>'
        shipname = html.escape(user.shipname)
        title = f'Ship "{shipname}"'
        canvas = render_canvas(session, user.shipname)

        content = f"""
        <div id="content">
            <h1> Ship "{shipname}"
                <form method="POST" style="display: contents"><input type="hidden" name="action" value="tick" /><input type="submit" value="&#8635; Refresh" style="width: max-content; padding: 0 0.5rem; margin: 0" /></form>
            </h1>
            <div id="ship-wrapper">
                <div id="components">
                    <input id="component-light" type="radio" name="component" value="light" checked /> <label for="component-light">Light</label>
                    <input id="component-button" type="radio" name="component" value="button"> <label for="component-button">Button</label>
                    <input id="component-source" type="radio" name="component" value="source"> <label for="component-source">Source</label>
                    <br />
                    <label><input type="checkbox" id="connect-mode" /> Connect mode</label>
                </div>
                <div id="canvas" data-tooltip="Click to add">
                {canvas}
                </div>
            </div>
        </div>
        """

    return templates.TemplateResponse(
        request=request, name="lamp.html",
        context={"title": title, "buttons": buttons, "overviewButtons": overviewButtons, "content": content},
    )


class MainPost(BaseModel):
    action: str = ""
    x: str = ""
    y: str = ""
    typ: str = ""
    left: str = ""
    right: str = ""
    id: str = ""


@app.post("/")
async def rootPost(request: Request, session: SessionDep, data: Annotated[MainPost, Form()]):
    user = get_logged_in_user(request, session)
    if not user:
        return RedirectResponse("/", status_code=HTTP_302_FOUND)

    shipname = user.shipname

    try:
        if data.action == "add":
            count = len(session.exec(select(Components.id).where(Components.ship == shipname)).all())
            if count < MAX_COMPONENTS and data.typ in COMPONENT_TYPES:
                session.add(Components(
                    x=float(data.x),
                    y=float(data.y),
                    type=data.typ,
                    state=1 if data.typ == "source" else 0,
                    properties="off",
                    ship=shipname,
                ))
                session.commit()

        elif data.action == "connect":
            src, dst = int(data.left), int(data.right)
            # Both ends must belong to this user's ship, and the wire must not exist yet
            owned = session.exec(
                select(Components.id).where(Components.id.in_([src, dst]), Components.ship == shipname)
            ).all()
            if src != dst and len(owned) == 2 and session.get(Connections, (src, dst)) is None:
                session.add(Connections(src=src, dst=dst))
                session.commit()

        elif data.action == "toggle":
            comp = session.exec(
                select(Components).where(
                    Components.id == int(data.id),
                    Components.type == "button",
                    Components.ship == shipname,
                )
            ).first()
            if comp:
                comp.properties = "off" if comp.properties == "on" else "on"
                session.add(comp)
                session.commit()
            tick(session, shipname)  # tick one updates the button state
            tick(session, shipname)  # tick two updates connected components

        elif data.action == "tick":
            tick(session, shipname)

    except ValueError:
        # Non-numeric x / y / ids from the form: ignore the request
        session.rollback()

    return RedirectResponse("/", status_code=HTTP_302_FOUND)


# ---------------------------------------------------------------- auth pages (unchanged apart from small fixes)

@app.get("/register")
async def registerGet(request: Request):
    title = "LAMP"
    overviewButtons = '<a class="menu-item" href="/">Overview</a>'
    buttons = (
        '<a class="menu-item" href="/login">Login</a>'
        '<a class="menu-item highlight" href="/register">Register</a>'
    )
    content = """
    <div id="content">
        <h1> Register</h1>
        <form method="POST"><label>Username:</label><input type="text" name="username" /><label>Password:</label><input type="text" name="password" /><label>Name of ship:</label><input type="text" name="shipname" /><input type="submit" value="Register" /></form>
    </div>
    """
    return templates.TemplateResponse(
        request=request, name="lamp.html",
        context={"title": title, "buttons": buttons, "overviewButtons": overviewButtons, "content": content},
    )


@app.get("/login")
async def loginGet(request: Request):
    title = "LAMP"
    overviewButtons = '<a class="menu-item" href="/">Overview</a>'
    buttons = (
        '<a class="menu-item highlight" href="/login">Login</a>'
        '<a class="menu-item" href="/register">Register</a>'
    )
    content = """
    <div id="content">
        <h1> Login</h1>
        <form method="POST"><label>Username:</label><input type="text" name="username" /><label>Password:</label><input type="text" name="password" /><input type="submit" value="Log In" /></form>
    </div>
    """
    return templates.TemplateResponse(
        request=request, name="lamp.html",
        context={"title": title, "buttons": buttons, "overviewButtons": overviewButtons, "content": content},
    )


class Login(BaseModel):
    username: str = ""
    password: str = ""


@app.post("/login")
async def loginPost(request: Request, data: Annotated[Login, Form()], session: SessionDep):
    title = "LAMP"
    overviewButtons = '<a class="menu-item" href="/">Overview</a>'
    buttons = (
        '<a class="menu-item highlight" href="/login">Login</a>'
        '<a class="menu-item" href="/register">Register</a>'
    )

    user = session.get(User, data.username)
    logged_in = bool(user) and user.password == data.password[:200]

    if logged_in:
        content = """
        <div id="content">
            <h1> Login</h1>
            <p>Successfully logged in</p>
            <meta http-equiv="Refresh" content="2;url=/" />
        </div>
        """
    else:
        content = """
        <div id="content">
            <h1> Login</h1>
            <p>Failed to log in</p>
            <form method="POST"><label>Username:</label><input type="text" name="username" /><label>Password:</label><input type="text" name="password" /><input type="submit" value="Log In" /></form>
        </div>
        """

    response = templates.TemplateResponse(
        request=request, name="lamp.html",
        context={"title": title, "buttons": buttons, "overviewButtons": overviewButtons, "content": content},
    )
    if logged_in:
        response.set_cookie(key="Session", value=user.session_id)
    return response


class Register(BaseModel):
    username: str = ""
    password: str = ""
    shipname: str = ""


@app.post("/register")
async def registerPost(request: Request, data: Annotated[Register, Form()], session: SessionDep):
    title = "LAMP"
    overviewButtons = '<a class="menu-item" href="/">Overview</a>'
    buttons = (
        '<a class="menu-item" href="/login">Login</a>'
        '<a class="menu-item highlight" href="/register">Register</a>'
    )

    registeredUser = None
    if session.get(User, data.username) is None:
        session_id = "".join(random.SystemRandom().choices(string.ascii_letters + string.digits, k=32))
        registeredUser = User(
            username=data.username,
            password=data.password[:200],
            shipname=data.shipname,
            session_id=session_id,
        )
        session.add(registeredUser)
        session.commit()
        session.refresh(registeredUser)

    if registeredUser:
        content = """
        <div id="content">
            <h1> Register</h1>
            <p>Successfully registered account</p>
            <meta http-equiv="Refresh" content="2;url=/" />
        </div>
        """
    else:
        content = """
        <div id="content">
            <h1> Register</h1>
            <p>Account already exists</p>
            <form method="POST"><label>Username:</label><input type="text" name="username" /><label>Password:</label><input type="text" name="password" /><label>Name of ship:</label><input type="text" name="shipname" /><input type="submit" value="Register" /></form>
        </div>
        """

    response = templates.TemplateResponse(
        request=request, name="lamp.html",
        context={"title": title, "buttons": buttons, "overviewButtons": overviewButtons, "content": content},
    )
    if registeredUser:
        response.set_cookie(key="Session", value=registeredUser.session_id)
    return response


@app.get("/logout")
async def logout():
    response = RedirectResponse("/", status_code=HTTP_302_FOUND)
    response.delete_cookie(key="Session")
    return response


print("Running server")
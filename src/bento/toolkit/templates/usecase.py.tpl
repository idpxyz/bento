from application.usecase import UseCase
from application.dto import BaseModel

class {{Name}}Input(BaseModel):
    pass

class {{Name}}Output(BaseModel):
    ok: bool = True

class {{Name}}(UseCase[{{Name}}Input, {{Name}}Output]):
    async def __call__(self, inp: {{Name}}Input) -> {{Name}}Output:
        return {{Name}}Output()

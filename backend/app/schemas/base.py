from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    # Campos desconhecidos sao rejeitados para evitar que o cliente pense que
    # alterou uma propriedade que o backend silenciosamente ignorou.
    model_config = ConfigDict(from_attributes=True, extra="forbid")

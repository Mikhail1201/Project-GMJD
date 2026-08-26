from dataclasses import asdict, dataclass, fields


@dataclass
class ModeloBase:
    @classmethod
    def desde_fila(cls, fila):
        if fila is None:
            return None
        datos = dict(fila)
        return cls(**{campo.name: datos.get(campo.name) for campo in fields(cls)})

    def a_dict(self) -> dict:
        return asdict(self)

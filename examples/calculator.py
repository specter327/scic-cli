from datavalue import ComplexData, PrimitiveData, ValidationMode
from scic import Executable, SCIC
from scic_cli import CLIConfig, SCICCLI


def primitive(data_type, name):
    return PrimitiveData(
        data_type=data_type,
        value=None,
        name=name,
        data_class=True,
    )


def signature(name, *schemas):
    return ComplexData(
        data_type=list,
        value=None,
        name=name,
        possible_values=schemas,
        data_class=True,
        validation_mode=ValidationMode.POSITIONAL,
    )


def add(a: int, b: int) -> int:
    return a + b


def build_application() -> SCIC:
    scic = SCIC(root_name="calculator")
    math = scic.create_context("math", description="Mathematical functions.")
    scic.register_function(
        adapter=Executable(
            name="add",
            description="Add two integers.",
            parameters=signature("parameters", primitive(int, "a"), primitive(int, "b")),
            results=signature("results", primitive(int, "sum")),
        ),
        function=add,
        context=math,
    )
    return scic.freeze()


application = build_application()


if __name__ == "__main__":
    SCICCLI(
        application,
        config=CLIConfig(application_name="SCIC Calculator"),
    ).run()

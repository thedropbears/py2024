# py2024

The Drop Bears' robot code for FRC 2024

## Setup

### Install dependencies

We use `pdm` to manage our dependencies in a virtual environment.

First, install `pdm`, either by using your system package manager, using [`pipx`][],
or following the instructions on the [`pdm` website][].

[`pipx`]: https://pipx.pypa.io
[`pdm` website]: https://pdm-project.org

After installing `pdm`, use it to create a virtual environment and install our dependencies.

```sh
pdm install
```

### pre-commit

[pre-commit][] is configured to run our formatters and linters.
These are enforced for all code committed to this project.

You must install pre-commit outside of this project's virtual environment.
Either use your system package manager, or use `pipx`:

```
pipx install pre-commit
```

Setup the pre-commit hooks to run on commit:
```
pre-commit install
```

[pre-commit]: https://pre-commit.com

## Run

### Simulation

```
pdm run robotpy sim
```

### Deploy to Robot

Once on robots network

```
pdm run deploy
```

### Test

```
pdm run test
```


## Code Structure

We use RobotPy's Magicbot framework

`robot.py`: Entry point, has mapping from driver inputs to high level robot actions.

`components/`: Abstracts hardware into robot actions.

`controllers/`: Automates robot actions, mostly with state machines.

`autonomous/`: Controls robot during autonomous period.

`ids.py`: Has CAN ids, PH channels and other port numbers.

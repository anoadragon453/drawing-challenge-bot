# Drawing Challenge Bot

A short bot written with [nio-template](https://github.com/anoadragon453/nio-template).

Posts the bi-weekly drawing challenge from
https://old.reddit.com/r/MLPDrawingSchool weekly to matrix rooms.

## Install

drawing-challenge-bot requires
[matrix-nio](https://github.com/matrix-org/matrix-nio), which supports
participation in end-to-end encryption rooms! To do so, it makes use of the
[libolm](https://gitlab.matrix.org/matrix-org/olm) C library.  This library
must be installed to allow for end-to-end encryption functionality, and
unfortunately it is *also* required for functional message polling, so it is
practically a hard required for this program.

Unfortunately, installation of this library can be non-trivial on some
platforms. However, with the power of docker, dependencies can be handled with
little fuss, and it is thus the recommended method of installing
`drawing-challenge-bot`. Native installation instructions are also provided, but
be aware that they are more complex.

### Docker

**Recommended.** Follow the docker [installation instructions](docker/README.md#setup).

### Native installation

#### Install libolm

You can install [libolm](https://gitlab.matrix.org/matrix-org/olm) from source,
or alternatively, check your system's package manager. Version `3.0.0` or
greater is required.

**(Optional) postgres development headers**

By default, drawing-challenge-bot uses SQLite as its storage backend. This is
fine for a few hundred users, but if you plan to support a much higher volume
of requests, you may consider using Postgres as a database backend instead.

If you want to use postgres as a database backend, you'll need to install
postgres development headers:

Debian/Ubuntu:

```
sudo apt install libpq-dev libpq5
```

Arch:

```
sudo pacman -S postgresql-libs
```

#### Install Python dependencies

Create and activate a Python 3 virtual environment:

```
virtualenv -p python3 env
source env/bin/activate
```

Install python dependencies:

```
pip install drawing-challenge-bot
```

## Configuration

Copy the sample configuration file to a new `config.yaml` file.

```
cp sample.config.yaml config.yaml
```

Edit the config file. The `matrix` section must be modified at least.

## Running

### Docker

Refer to the docker [run instructions](docker/README.md#running).

### Native installation

Make sure to source your python environment if you haven't already:

```
source env/bin/activate
```

Then simply run the bot with:

```
drawing-challenge-bot
```

By default, the bot will run with the config file at `./config.yaml`. However, an
alternative relative or absolute filepath can be specified after the command:

```
drawing-challenge-bot other-config.yaml
```

## Usage

Invite the bot to a room and it should accept the invite and join. It will then
start posting challenges.

## Development

Please see [CONTRIBUTING.md](CONTRIBUTING.md).

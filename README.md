# Atria Calendar

Event scheduling and volunteer management platform


## Environment Setup

```bash
cd atria-calendar
virtualenv --python=python3.6 venv
source venv/bin/activate
```


## Install and run Atria Calendar

Install dependencies:

```bash
cd atriaapp
pip install -r requirements/demo.txt
```

Build app:

```bash
cd atria-calendar/atriaaapp
python manage.py makemigrations
python manage.py migrate
python manage.py loaddata sample-data
```

Note that the last step loads some sample data from the fixture sample-data.json.

This also creates an admin user admin@mail.com with password pass1234

Run app:

```bash
python manage.py runserver
```

Navigate to http://localhost:8000/, or http://localhost:8000/admin and login as the admin user (admin@mail.com/pass1234).


## Atria Indy Community Demo (Consent to use Data)

There is a video demo of the VCX solution here:

https://zoom.us/recording/share/wwD9uRGKRg31nPeI7MtYVpa-ufHowox1gNUaCNO7dmOwIumekTziMw

It shows the credential flow implementing the data use consent process (user is consenting for their health data to be used for research purposes):

0:00 - setup of organizations, schema and credential definitions
8:00 - MYco issues health credentials to Alice
16:00 - IRB issues research project credential to researcher
19:40 - Researcher issues consent enablement credential to Alice
23:40 - Researcher asks Alice to provide proof of eligibility (zero knowledge proof)
30:00 - Researcher asks Alice to provide data with consent (revealed attributes)


## Install and run Atria Indy Community

There are two options to run the environment locally - running in docker (recommended) or running all the services locally.

### Running Atria Indy Community - Docker Version

1. Open two bash shells, and run the following commands:

```bash
git clone https://github.com/ianco/von-network.git
cd von-network
./manage build
./manage start
```

... and:

```bash
cd atria-calendar/docker
./base-image  # note this takes about 30 mintues
./manage start
```

That's it!  Your docker is up and running, open a browser and navigate to http://localhost:8000/

To shut down the environment, <CTRL-C> to stop the docker services and then in each shell run:

```bash
./manage rm
```


### Running Atria Indy Community - "Bare Metal" Version

If you compare to the previous option, these are basically all the steps executed to build the docker environment.

Note it is recommended to build/run on either Ubuntu 16.04 or on the latest Mac o/s.

1. Check out the following github repositories:

```bash
git clone https://github.com/ianco/indy-sdk.git
cd indy-sdk
git checkout vcx_updates
cd ..
git clone https://github.com/ianco/von-network.git
```

Note that these are the "ianco" forks of the master repositories (and "vcx_updates" brach of indy-sdk) as they contain updates/fixes that are not yet PR'ed.

1a. Install dependencies in von-network:

```bash
cd von-network
virtualenv --python=python3.6 venv
source venv/bin/activate
pip install -r server/requirements.txt
```

2. In the indy-sdk repository, build all necessary libraries (check the indy-sdk repo for dependencies, such as rust):

```bash
cd indy-sdk
cd libindy
cargo build
ln -s target/debug/libindy.so /use/local/lib/
cd ..

cd experimental/plugins/postgres_storage
cargo build
ln -s target/debug/libindystrgpostgres.so /use/local/lib/
cd ../../..

cd cli
cargo build
cd ..

cd libnulpay
cargo build
ln -s target/debug/libnullpay.so /use/local/lib/
cd ..

cd vcx
cd libvcx
cargo build
ln -s target/debug/libvcx.so /use/local/lib/
cd ..

cd dummy-cloud-agent
cargo build
```

3. In the root indy-sdk directory, build and run the indy nodes:

```bash
docker build -f ci/indy-pool.dockerfile -t indy_pool .
docker run -itd -p 9701-9708:9701-9708 indy_pool
```

... and run a postgres database:

```bash
docker run --name some-postgres -e POSTGRES_PASSWORD=mysecretpassword -d -p 5432:5432 postgres -c 'log_statement=all' -c 'logging_collector=on' -c 'log_destination=stderr'
```

4. In a separate shell, run the VCX cloud agent:

```bash
cd indy-sdk/vcx/dummy-cloud-agent
cargo run config.json
```

5. Open 2 shells to run the Atria Indy Community edition:

```bash
cd atria-calendar/atriaapp
python manage.py runserver
```

... and run the "virtual agent" bot:

```bash
cd atria-calendar/atriaapp
python manage.py process_tasks
```

6. Whew!  One more - start up the von-network ledger browser - this also provides the capability to register DID's on the ledger for our Atria organizations:

```bash
cd von-network
GENESIS_FILE=/tmp/atria-genesis.txt PORT=9000 python -m server.server
```

Note that the genesis file at the above location is created by Atria Indy Community on startup.


### Reset the Atria Indy Community environment

To reset the environment and start from scratch:

1. Shut down the von-network ledger browser and vcx dummy-cloud-agent (just CRTL-C to kill each of these processes), and then:

```bash
rm -rf ~/.indy_client/
```

2. Kill the two Atria processes (CTRL-C) and reload the Atria database:

```bash
cd atria-calendar/atriaapp
./reload_db.sh
```

3. Kill the 2 docker processes (indy nodes and postgres database):

```bash
# to kill the 2 specific dockers:
docker ps   # (get the process id's)
docker stop <process 1> <process 2>
docker rm -f <process 1> <process 2>
# ... or to indescriminitely kill all dockers:
docker ps -q  | xargs docker rm -f
```

To re-start the environment, just go to step #1 of the previous section.


## Atria Indy Community - Credential Issuance and Proof Request Scenarios

1. Create a "Trustee" organization

2. Create one or more "Issuing" organizations

3. Register one or more end users

4. As an Issuing organzation, establish a Connection with an end user

5. As an Issuing organization, issue a Credential to an end user

6. As an Issuing organization, request a Proof from an end user


Navigate to http://localhost:8000/, or http://localhost:8000/admin and login as the admin user (admin@mail.com/pass1234).



## Connecting to the Sovrin Test Network (STN)

For a connection from VerityUI to the enterprise agency, (https://eas01.pps.evernym.com 4), the pool that should be connected to is the STN (Sovrin Test Network). The genesis file is in Github, but that seems to be down this morning. If you ping me in sovin slack I’ll put it in there.


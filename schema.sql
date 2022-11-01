CREATE TABLE "user" (
	id serial PRIMARY KEY,
	username character varying(256) UNIQUE,
	created timestamp without time zone NOT NULL,
	updated timestamp without time zone NOT NULL,
	oauth_token character varying(256),
	oauth_token_expires timestamp without time zone,
	oauth_token_scopes character varying,
	email character varying(256) NOT NULL,
	user_type character varying DEFAULT 'active_non_paying'::character varying NOT NULL,
	url character varying(256),
	location character varying(256),
	bio character varying(4096),
	oauth_revocation_token character varying(256),
	suspension_notice character varying(4096)
);

CREATE INDEX ix_user_username ON "user" USING btree (username);

CREATE TABLE backing_repo (
	id serial PRIMARY KEY,
	new boolean NOT NULL,
	name character varying(256) NOT NULL,
	ref character varying(1024) NOT NULL,
	commit_sha character varying(256),
	commit_author character varying(256),
	commit_email character varying(256),
	commit_time character varying(256),
	commit_message character varying(1024),
	tree_sha character varying(256),
	resource_id integer
);

CREATE TABLE wiki (
	id serial PRIMARY KEY,
	created timestamp without time zone NOT NULL,
	updated timestamp without time zone NOT NULL,
	name character varying(256) NOT NULL,
	owner_id integer NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
	visibility character varying NOT NULL,
	repo_id integer NOT NULL REFERENCES backing_repo(id)
);

CREATE TABLE root_wiki (
	id integer NOT NULL PRIMARY KEY REFERENCES wiki(id)
);

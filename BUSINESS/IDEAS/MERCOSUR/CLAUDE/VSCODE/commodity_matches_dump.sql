--
-- PostgreSQL database dump
--

\restrict iMIkgAn6ZgNoWwCt4EridJCxz2sIeMDZIOH8dGqnuEdO2RB7sD3myU5uCMO4saf

-- Dumped from database version 15.15 (Debian 15.15-0+deb12u1)
-- Dumped by pg_dump version 15.15 (Debian 15.15-0+deb12u1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: commodity_matches; Type: TABLE; Schema: public; Owner: tudor
--

CREATE TABLE public.commodity_matches (
    id integer NOT NULL,
    commodity character varying(50),
    supplier_name character varying(500),
    supplier_country character(2),
    supplier_email character varying(200),
    supplier_website character varying(500),
    buyer_name character varying(500),
    buyer_country character(2),
    buyer_email character varying(200),
    match_type character varying(20),
    confidence numeric(3,2),
    created_at timestamp without time zone DEFAULT now()
);


ALTER TABLE public.commodity_matches OWNER TO tudor;

--
-- Name: commodity_matches_id_seq; Type: SEQUENCE; Schema: public; Owner: tudor
--

CREATE SEQUENCE public.commodity_matches_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.commodity_matches_id_seq OWNER TO tudor;

--
-- Name: commodity_matches_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: tudor
--

ALTER SEQUENCE public.commodity_matches_id_seq OWNED BY public.commodity_matches.id;


--
-- Name: commodity_matches id; Type: DEFAULT; Schema: public; Owner: tudor
--

ALTER TABLE ONLY public.commodity_matches ALTER COLUMN id SET DEFAULT nextval('public.commodity_matches_id_seq'::regclass);


--
-- Data for Name: commodity_matches; Type: TABLE DATA; Schema: public; Owner: tudor
--

COPY public.commodity_matches (id, commodity, supplier_name, supplier_country, supplier_email, supplier_website, buyer_name, buyer_country, buyer_email, match_type, confidence, created_at) FROM stdin;
\.


--
-- Name: commodity_matches_id_seq; Type: SEQUENCE SET; Schema: public; Owner: tudor
--

SELECT pg_catalog.setval('public.commodity_matches_id_seq', 1, false);


--
-- Name: commodity_matches commodity_matches_pkey; Type: CONSTRAINT; Schema: public; Owner: tudor
--

ALTER TABLE ONLY public.commodity_matches
    ADD CONSTRAINT commodity_matches_pkey PRIMARY KEY (id);


--
-- Name: idx_commodity_matches_buyer_email; Type: INDEX; Schema: public; Owner: tudor
--

CREATE INDEX idx_commodity_matches_buyer_email ON public.commodity_matches USING btree (buyer_email);


--
-- Name: idx_commodity_matches_commodity; Type: INDEX; Schema: public; Owner: tudor
--

CREATE INDEX idx_commodity_matches_commodity ON public.commodity_matches USING btree (commodity);


--
-- PostgreSQL database dump complete
--

\unrestrict iMIkgAn6ZgNoWwCt4EridJCxz2sIeMDZIOH8dGqnuEdO2RB7sD3myU5uCMO4saf


import os
from flask import Flask, jsonify, request, render_template, send_file, Response
from providers.grocery_cli import GroceryCLI, ProviderError
from database import init_db, save_search, save_comparison, catalog_stats

app=Flask(__name__, template_folder="templates")
grocery=GroceryCLI()

try:
    init_db()
    DB_READY=True
    DB_ERROR=None
except Exception as exc:
    DB_READY=False
    DB_ERROR=str(exc)

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/static_zxing")
def static_zxing():
    p=os.path.join(os.path.dirname(__file__),"vendor","zxing.min.js")
    if os.path.exists(p):
        return send_file(p,mimetype="application/javascript")
    return Response("/* ZXing no disponible */",mimetype="application/javascript")

@app.route("/api/health")
def health():
    status={
        "ok": True,
        "app":"CestaSmart 3.1 Cloud",
        "grocery_cli":grocery.available(),
        "database":DB_READY,
    }
    if DB_ERROR:
        status["database_error"]=DB_ERROR
    return jsonify(status), 200 if grocery.available() else 503

@app.route("/api/diagnose/<store>")
def diagnose_store(store):
    return jsonify(grocery.diagnose_store(store))

@app.route("/api/connectors")
def connectors():
    return jsonify(grocery.connector_status())

@app.route("/api/status")
def status():
    data={"app":"CestaSmart 3.1 Cloud","grocery":grocery.status(),"database":DB_READY}
    if DB_READY:
        try:data["catalog"]=catalog_stats()
        except Exception:pass
    return jsonify(data)

@app.route("/api/catalog/stats")
def stats():
    if not DB_READY:
        return jsonify({"error":"Base de datos no disponible"}),503
    try:return jsonify(catalog_stats())
    except Exception as e:return jsonify({"error":str(e)}),500

@app.route("/api/search")
def search():
    store=(request.args.get("store") or "").strip()
    q=(request.args.get("q") or "").strip()
    ean=(request.args.get("ean") or "").strip()
    if not store or not q:
        return jsonify({"error":"Faltan supermercado o producto"}),400
    try:
        result=grocery.search(store,q,8,ean=ean or None)
        if DB_READY:
            try:save_search(store,q,ean,result)
            except Exception as db_exc:result["catalog_warning"]=str(db_exc)
        return jsonify(result)
    except ProviderError as e:
        return jsonify({"error":str(e)}),503


@app.route("/api/optimize",methods=["POST"])
def optimize():
    b=request.get_json(force=True) or {}
    try:
        return jsonify(grocery.optimize(
            b.get("stores") or [],
            b.get("items") or [],
            b.get("options") or {}
        ))
    except ProviderError as e:
        return jsonify({"error":str(e)}),503

@app.route("/api/compare",methods=["POST"])
def compare():
    b=request.get_json(force=True) or {}
    try:
        result=grocery.compare(b.get("stores") or [],b.get("items") or [])
        if DB_READY:
            try:save_comparison(b,result)
            except Exception as db_exc:result["catalog_warning"]=str(db_exc)
        return jsonify(result)
    except ProviderError as e:
        return jsonify({"error":str(e)}),503

if __name__=="__main__":
    port=int(os.environ.get("PORT","5061"))
    app.run(host="0.0.0.0",port=port,debug=False)

from app import create_app
import os

app = create_app()

# 🔎 DEBUG: imprimir rutas registradas
print("\n=== RUTAS REGISTRADAS ===")
for rule in app.url_map.iter_rules():
    print(f"{rule.rule}  ->  {rule.methods}")
print("========================\n")

if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port, debug=False)


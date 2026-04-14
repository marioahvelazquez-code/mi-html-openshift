import "./App.css";
import Header from "./components/Header";
import Footer from "./components/Footer";
import FotosPage from "./modules/fotos/FotosPage";

function App() {
  return (
    <div className="app-layout">
      <Header />

      <main className="app-content">
        <FotosPage />
      </main>

      <Footer />
    </div>
  );
}

export default App;

import React from "react";
import { Link } from "react-router-dom";

type CardSeccionProps = {
  imageUrl: string;
  icon: React.ReactNode;
  title: string;
  description: string;
  to?: string; // opcional
  onClick?: () => void; // opcional
};

const CardSeccion: React.FC<CardSeccionProps> = ({
  imageUrl,
  icon,
  title,
  description,
  to,
  onClick,
}) => {
  const cardContent = (
    <div
      className="card card-seccion h-100 tamanio sombra"
      onClick={onClick}
      style={{ cursor: onClick ? "pointer" : "default" }}
    >
      <div className="card-header-gradiente text-white text-center py-2">
        {title}
      </div>

      <div className="card-img-container overflow-hidden">
        <img src={imageUrl} className="card-img-top card-img-hover" />
      </div>

      <div className="card-body d-flex align-items-center gap-3">
        <div className="icono text-primary fs-4">{icon}</div>
        <div>
          <p className="card-text text-secondary mb-0">
            <strong>{description}</strong>
          </p>
        </div>
      </div>
    </div>
  );

  // 🔀 Si hay "to", navegamos
  if (to) {
    return (
      <Link to={to} className="text-decoration-none">
        {cardContent}
      </Link>
    );
  }

  // 🖱️ Si no, solo devolvemos la card
  return cardContent;
};

export default CardSeccion;

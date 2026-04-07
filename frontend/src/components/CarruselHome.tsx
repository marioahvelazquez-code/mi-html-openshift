import Carousel from "react-bootstrap/Carousel";

import img1 from "../assets/img/slide1.jpg";

export default function CarruselHome() {
  return (
    <Carousel controls={false} indicators={false}>
      <Carousel.Item
        style={{ backgroundImage: `url(${img1})` }}
        className="carousel-item"
      ></Carousel.Item>
    </Carousel>
  );
}

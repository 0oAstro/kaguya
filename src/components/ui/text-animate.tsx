"use client";

import { motion, HTMLMotionProps } from "framer-motion";
import { FC } from "react";

type AnimationType =
  | "fadeIn"
  | "fadeInUp"
  | "popIn"
  | "shiftInUp"
  | "rollIn"
  | "whipIn"
  | "whipInUp"
  | "calmInUp";

interface Props extends HTMLMotionProps<"div"> {
  text: string;
  type?: AnimationType;
  delay?: number;
  duration?: number;
}

const animationVariants = {
  fadeIn: {
    initial: { opacity: 0 },
    animate: { opacity: 1 },
  },
  fadeInUp: {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
  },
  popIn: {
    initial: { opacity: 0, scale: 0.8 },
    animate: { opacity: 1, scale: 1 },
  },
  shiftInUp: {
    initial: { opacity: 0, y: 25, rotate: 10 },
    animate: { opacity: 1, y: 0, rotate: 0 },
  },
  rollIn: {
    initial: { opacity: 0, rotate: -30, x: -25 },
    animate: { opacity: 1, rotate: 0, x: 0 },
  },
  whipIn: {
    initial: { opacity: 0, scale: 0.8, rotate: -10 },
    animate: { opacity: 1, scale: 1, rotate: 0 },
  },
  whipInUp: {
    initial: { opacity: 0, y: 30, scale: 0.8 },
    animate: { opacity: 1, y: 0, scale: 1 },
  },
  calmInUp: {
    initial: { opacity: 0, y: 15 },
    animate: { opacity: 1, y: 0 },
  },
};

const TextAnimate: FC<Props> = ({
  text,
  type = "whipInUp",
  className,
  delay = 0,
  duration = 0.5,
  ...props
}: Props) => {
  const selectedAnimation = animationVariants[type];

  return (
    <motion.div
      className={className}
      initial={selectedAnimation.initial}
      animate={selectedAnimation.animate}
      transition={{
        duration,
        delay,
        ease: [0.25, 0.46, 0.45, 0.94],
      }}
      {...props}
    >
      {text}
    </motion.div>
  );
};

export default TextAnimate;

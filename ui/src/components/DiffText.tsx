import { Fragment } from "react";
import { isDiffLine } from "../lib/derive";

export default function DiffText({ text }: { text: string }) {
  return (
    <>
      {text.split("\n").map((ln, i) => {
        const d = isDiffLine(ln);
        return (
          <Fragment key={i}>
            <span
              className={
                d === "add"
                  ? "block bg-acc/10 text-acc"
                  : d === "del"
                    ? "block bg-err/10 text-err"
                    : d === "hunk"
                      ? "block text-acc/70"
                      : "block"
              }
            >
              {ln || " "}
            </span>
          </Fragment>
        );
      })}
    </>
  );
}
